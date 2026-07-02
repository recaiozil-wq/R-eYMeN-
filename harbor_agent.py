"""
ReYMeN Harbor Agent — Terminal-Bench 2.1 için custom adapter.

Kullanım:
    harbor run \\
      -d terminal-bench/terminal-bench-2-1 \\
      --agent-import-path "reymen.harbor_agent:ReYMeNAgent" \\
      -m deepseek/deepseek-v4-flash \\
      -k 5

Not: Agent container içinde çalışır, DeepSeek API'sine
internet üzerinden erişir. DEEPSEEK_API_KEY ortam değişkeni
gerekir (harbor'a --env ile geçirilir).
"""

import json
import os
import shlex
import uuid
from pathlib import Path
from typing import Any

from harbor.agents.base import BaseAgent
from harbor.agents.installed.base import BaseInstalledAgent
from harbor.environments.base import BaseEnvironment
from harbor.models.agent.context import AgentContext
from harbor.models.trajectories import (
    Agent as TrajAgent,
    FinalMetrics,
    Observation,
    ObservationResult,
    Step,
    ToolCall,
    Trajectory,
)


class ReYMeNAgent(BaseInstalledAgent):
    """
    ReYMeN AI agent adapted for Harbor/Terminal-Bench.
    
    Setup:
      - Python 3 + pip kurar
      - requests, pyyaml bağımlılıklarını yükler
      - tbench_plan_recovery.py'yi container'a kopyalar
    
    Run:
      - Görev talimatını alır
      - tbench_plan_recovery.py'yi çalıştırır
      - Çıktıyı log dosyasına yazar
    """

    SUPPORTS_ATIF: bool = True
    SUPPORTS_WINDOWS: bool = False

    @staticmethod
    def name() -> str:
        return "reymen"

    def version(self) -> str | None:
        return self._version or "2026.07.02"

    def get_version_command(self) -> str | None:
        return 'echo "ReYMeN Agent 2026.07.02"'

    async def install(self, environment: BaseEnvironment) -> None:
        """Container içine Python ve bağımlılıkları kur."""
        # Sistem paketleri
        await self.exec_as_root(
            environment,
            command=(
                "apt-get update && "
                "apt-get install -y python3 python3-pip curl git "
                "DEBIAN_FRONTEND=noninteractive"
            ),
            timeout_sec=120,
        )
        
        # Python bağımlılıkları
        await self.exec_as_agent(
            environment,
            command="python3 -m pip install requests pyyaml 2>&1 | tail -3",
            timeout_sec=60,
        )
        
        # tbench_plan_recovery.py'yi kopyala
        script_dir = Path(__file__).parent.parent
        script_path = script_dir / "tbench_plan_recovery.py"
        
        if script_path.exists():
            script_content = script_path.read_text()
            escaped = script_content.replace("'", "'\\''")
            await self.exec_as_agent(
                environment,
                command=(
                    f"cat > /home/user/tbench_plan_recovery.py << 'SCRIPTEOF'\n"
                    f"{script_content}\n"
                    f"SCRIPTEOF"
                ),
                timeout_sec=10,
            )
            await self.exec_as_root(
                environment,
                command="chmod +x /home/user/tbench_plan_recovery.py",
            )

    def populate_context_post_run(self, context: AgentContext) -> None:
        """Çalışma sonrası context'e token/metrik bilgisi yaz."""
        log_path = self.logs_dir / "reymen-output.txt"
        if log_path.exists():
            text = log_path.read_text()
            # Basit token sayısı tahmini
            context.n_input_tokens = len(text) // 2
            context.n_output_tokens = 0

    async def run(
        self,
        instruction: str,
        environment: BaseEnvironment,
        context: AgentContext,
    ) -> None:
        """Görevi çalıştır."""
        # API key'leri ilet
        env = {}
        deepseek_key = os.environ.get("DEEPSEEK_API_KEY")
        if deepseek_key:
            env["DEEPSEEK_API_KEY"] = deepseek_key
        
        model = self.model_name or "deepseek/deepseek-v4-flash"
        env["REYMEN_MODEL"] = model
        
        env["HARBOR_INSTRUCTION"] = instruction
        
        # tbench_plan_recovery.py'yi çalıştır
        run_cmd = (
            "cd /home/user && "
            f"python3 tbench_plan_recovery.py "
            f"--task '{shlex.quote(instruction)}' "
            f"--model {shlex.quote(model)} "
            f"2>&1 | tee {shlex.quote(str(self.logs_dir / 'reymen-output.txt'))}"
        )
        
        try:
            await self.exec_as_agent(
                environment,
                command=run_cmd,
                env=env,
                timeout_sec=600,
            )
        except Exception as e:
            self.logger.error(f"ReYMeN agent failed: {e}")
            raise
