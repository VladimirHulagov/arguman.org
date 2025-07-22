from django.dispatch import Signal

added_premise_for_contention = Signal(["premise"])
added_premise_for_premise = Signal(["premise"])
reported_as_fallacy = Signal(["report"])
supported_a_premise = Signal(["premise", "user"])
