import subprocess
import tempfile
import os
import logging

def run_agent_in_docker(code_payload: str, timeout_seconds: int = 10) -> dict:
    """
    Executes raw python agent code inside a secure, ephemeral Docker container
    with strict CPU, memory, and time limits.
    """
    # Create a temporary file for the code payload
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as temp_file:
        temp_file.write(code_payload)
        temp_file_path = temp_file.name

    container_name = f"viloura_sandbox_{os.path.basename(temp_file_path).split('.')[0]}"
    
    # Docker run command with strict security constraints:
    # --network none: No internet access
    # --memory 256m: Max 256MB RAM
    # --cpus 0.5: Max half a CPU core
    docker_cmd = [
        "docker", "run", "--rm",
        "--name", container_name,
        "--network", "none",
        "--memory", "256m",
        "--cpus", "0.5",
        "-v", f"{temp_file_path}:/app/agent.py:ro",
        "python:3.10-slim",
        "python", "/app/agent.py"
    ]

    try:
        result = subprocess.run(
            docker_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=timeout_seconds
        )
        
        # Cleanup temp file
        os.unlink(temp_file_path)
        
        if result.returncode == 0:
            return {
                "status": "success",
                "output": result.stdout.strip(),
                "error": None
            }
        else:
            return {
                "status": "error",
                "output": result.stdout.strip(),
                "error": result.stderr.strip()
            }

    except subprocess.TimeoutExpired:
        # Cleanup container if timed out
        subprocess.run(["docker", "rm", "-f", container_name], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if os.path.exists(temp_file_path):
            os.unlink(temp_file_path)
        return {
            "status": "timeout",
            "output": "",
            "error": f"Execution exceeded safety timeout of {timeout_seconds} seconds."
        }
    except Exception as e:
        if os.path.exists(temp_file_path):
            os.unlink(temp_file_path)
        return {
            "status": "failure",
            "output": "",
            "error": str(e)
        }
