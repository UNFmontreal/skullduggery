import nireports.report as report


class DefaceReport(report.Report):
    def __init__(self, subject, session=None):
        super().__init__(subject, session)
        self.subject = subject
