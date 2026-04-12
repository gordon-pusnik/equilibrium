import unittest

from app.models.coach_api_models import MistakeSeverity
from app.services.coach.classifiers import classify_mistake_severity


class CoachClassifierTests(unittest.TestCase):
    def test_severity_threshold_boundaries(self):
        self.assertEqual(classify_mistake_severity(0.0), MistakeSeverity.PERFECT)
        self.assertEqual(classify_mistake_severity(0.0001), MistakeSeverity.VERY_CLOSE)
        self.assertEqual(classify_mistake_severity(0.0499), MistakeSeverity.VERY_CLOSE)
        self.assertEqual(classify_mistake_severity(0.05), MistakeSeverity.SMALL_LEAK)
        self.assertEqual(classify_mistake_severity(0.1499), MistakeSeverity.SMALL_LEAK)
        self.assertEqual(classify_mistake_severity(0.15), MistakeSeverity.MODERATE)
        self.assertEqual(classify_mistake_severity(0.3499), MistakeSeverity.MODERATE)
        self.assertEqual(classify_mistake_severity(0.35), MistakeSeverity.MAJOR)
