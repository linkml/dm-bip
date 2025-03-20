"""The pipeline runner TUI."""

import os
import subprocess
from dataclasses import dataclass
from pathlib import Path

from textual import events, on, work
from textual.app import App, ComposeResult
from textual.containers import Center, Container, Horizontal, VerticalGroup
from textual.message import Message
from textual.reactive import reactive
from textual.widgets import Button, Footer, Header, LoadingIndicator, Log, Static
from textual.worker import Worker, WorkerState


@dataclass
class PipelineStep:
    command: str
    label: str
    stdout: Path
    stderr: Path


class PipelineStepWidget(VerticalGroup):
    class Started(Message):
        @property
        def control(self):
            print("getting the control")
            print(self)
            print(self._sender)
            return self._sender

    class Finished(Message):
        def __init__(self, return_code: int):
            self.return_code = return_code
            super().__init__()

        @property
        def control(self):
            return self._sender

    def __init__(self, step: PipelineStep) -> None:
        super().__init__()
        self.step = step

    @work(exclusive=True, thread=True)
    def run_process(self):
        stdout_fp = self.step.stdout.open("w")
        stderr_fp = self.step.stderr.open("w")
        self.post_message(self.Started())
        proc = subprocess.run(self.step.command.split(" "), stdout=stdout_fp, stderr=stderr_fp)
        self.post_message(self.Finished(proc.returncode))

    def on_worker_state_changed(self, event: Worker.StateChanged):
        if event.state == WorkerState.RUNNING:
            self.query_one("Button").loading = True
        elif event.state == WorkerState.PENDING:
            pass
        else:
            self.query_one("Button").loading = False

        # button.loading = False


    def compose(self) -> ComposeResult:
        with Center():
            yield Static('[b]' + self.step.label + '[/]')
            yield Static(self.step.command)
            yield Button("Run", variant="primary", id="run")
            # yield Button("Delete output", variant="error", id="delete")
            yield LoadingIndicator()

    async def on_button_pressed(self):
        self.run_process()
        # self.post_message(self.Triggered(self.step))


class PipelineRunnerApp(App):
    """The Textual object representing the Pipeline TUI."""

    CSS_PATH = "app.css"
    command_output = reactive("")

    def on_mount(self):
        self.begin_capture_print(self, True, True)

    def compose(self) -> ComposeResult:
        yield Header()
        yield Footer()

        with Horizontal():
            with Container():
                yield PipelineStepWidget(
                    PipelineStep(
                        "make test",
                        "1. Clean up data",
                        Path("output/1.log"),
                        Path("output/1.err.log"),
                    )
                )

                yield PipelineStepWidget(
                    PipelineStep(
                        "make install",
                        "2. Schema automator",
                        Path("output/2.log"),
                        Path("output/2.err.log"),
                    )
                )

                yield PipelineStepWidget(
                    PipelineStep(
                        "make filter_columns",
                        "3. Filter columns",
                        Path("output/3.log"),
                        Path("output/3.err.log"),
                    )
                )

            # yield Log()

    # @work(exclusive=True)
    # async def log_process(self, step: PipelineStep):
    #     log = self.query_one(Log)
    #     log.clear()

    #     args = step.command.split(" ")
    #     text = p.stdout.read1().decode("utf-8")
    #     log.write(text)

    def on_pipeline_step_widget_started(self, message: PipelineStepWidget.Started):
        pass
        # print("HELLO")
        # print(message.control)
        # print(message)
        # assert isinstance(message.control, PipelineStepWidget)
        # button = message.control.query_one("Button")
        # button.loading = True

    def on_pipeline_step_widget_finished(self, message: PipelineStepWidget.Finished):
        pass
        # print("FINISHED!")
        # print(message)
        # pass
        # assert isinstance(message.control, PipelineStepWidget)
        # button = message.control.query_one("Button")
        # button.loading = False

        # self.log_process(message.step)
        # with self.suspend():
        #     # subprocess.run(message.step.command.split(" "))
        #     os.system(message.step.command)


if __name__ == "__main__":
    app = PipelineRunnerApp()
    app.run()
