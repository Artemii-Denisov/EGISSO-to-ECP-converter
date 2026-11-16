"""Background worker thread for GUI processing."""

from __future__ import annotations

from PySide6.QtCore import QThread, Signal

from egisso_to_ecp.application.pipeline import ConversionPipeline
from egisso_to_ecp.domain.models import ConversionConfig, ConversionSummary


class ConversionWorker(QThread):
    """Executes the conversion pipeline in a dedicated background thread."""

    progress_changed = Signal(int, int, str)
    log_received = Signal(str)
    completed = Signal(object)
    failed = Signal(str)

    def __init__(self, config: ConversionConfig) -> None:
        super().__init__()
        self.config = config

    def run(self) -> None:
        try:
            pipeline = ConversionPipeline(
                config=self.config,
                progress_callback=self._on_progress,
                log_callback=self._on_log,
            )
            summary: ConversionSummary = pipeline.run()
            self.completed.emit(summary)
        except Exception as e:
            self.failed.emit(str(e))

    def _on_progress(self, current: int, total: int, status: str) -> None:
        self.progress_changed.emit(current, total, status)

    def _on_log(self, message: str) -> None:
        self.log_received.emit(message)
