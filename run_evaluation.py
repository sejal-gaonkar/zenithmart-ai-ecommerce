"""Run the ZenithMart chatbot and API test suites.

This evaluation uses mocked Gemini responses. A successful run validates
application logic and API wiring, not live Gemini credentials or availability.
"""

import os
import unittest

os.environ.setdefault("GEMINI_API_KEY", "test-gemini-key")


def run_all_evaluations() -> bool:
    print("\n" + "=" * 68)
    print("  ZenithMart E-Commerce Application Evaluation")
    print("=" * 68)

    suite = unittest.defaultTestLoader.discover(
        start_dir=os.path.dirname(os.path.abspath(__file__)),
        pattern="test_*.py",
    )
    result = unittest.TextTestRunner(verbosity=2).run(suite)

    print("\n" + "=" * 68)
    print("  Evaluation Summary")
    print("=" * 68)
    print(f"Tests run: {result.testsRun}")
    print(f"Passed: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print("=" * 68)

    return result.wasSuccessful()


if __name__ == "__main__":
    raise SystemExit(0 if run_all_evaluations() else 1)
