class VerificationEngine:

    def verify(self,
               diagnosis,
               remediation):

        try:
            return remediation.action()
        except Exception:
            return False
