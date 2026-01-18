"""
Unit Tests for Backchannel Detection

This script tests the backchannel detection logic without needing
to run the full agent. Use this to verify the detection works correctly.

Run with:
    python test_backchannel.py
"""

import sys
import os

# Add the interrupt_handler to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from interrupt_handler import (
    InterruptionConfig,
    BackchannelDetector,
    InterruptDecision,
)


def test_backchannels():
    """Test that backchannels are correctly identified."""
    detector = BackchannelDetector()
    
    # Test cases: (transcript, agent_speaking, expected_decision)
    test_cases = [
        # Scenario 1: Agent speaking + backchannel = IGNORE
        ("yeah", True, InterruptDecision.IGNORE),
        ("ok", True, InterruptDecision.IGNORE),
        ("okay", True, InterruptDecision.IGNORE),
        ("hmm", True, InterruptDecision.IGNORE),
        ("uh huh", True, InterruptDecision.IGNORE),
        ("right", True, InterruptDecision.IGNORE),
        ("mhm", True, InterruptDecision.IGNORE),
        ("yes", True, InterruptDecision.IGNORE),
        ("yep", True, InterruptDecision.IGNORE),
        ("sure", True, InterruptDecision.IGNORE),
        ("alright", True, InterruptDecision.IGNORE),
        
        # Scenario 2: Agent speaking + interrupt word = INTERRUPT
        ("stop", True, InterruptDecision.INTERRUPT),
        ("wait", True, InterruptDecision.INTERRUPT),
        ("no", True, InterruptDecision.INTERRUPT),
        ("hold on", True, InterruptDecision.INTERRUPT),
        ("actually", True, InterruptDecision.INTERRUPT),
        ("but wait", True, InterruptDecision.INTERRUPT),
        
        # Scenario 3: Agent silent + any input = PROCESS
        ("yeah", False, InterruptDecision.PROCESS),
        ("ok", False, InterruptDecision.PROCESS),
        ("stop", False, InterruptDecision.PROCESS),
        ("hello", False, InterruptDecision.PROCESS),
        
        # Scenario 4: Mixed input with interrupt word = INTERRUPT
        ("yeah but wait", True, InterruptDecision.INTERRUPT),
        ("ok but actually", True, InterruptDecision.INTERRUPT),
        ("hmm wait a second", True, InterruptDecision.INTERRUPT),
        ("yeah no stop", True, InterruptDecision.INTERRUPT),
        
        # Edge cases
        ("Yeah.", True, InterruptDecision.IGNORE),  # With punctuation
        ("OK!", True, InterruptDecision.IGNORE),    # With exclamation
        ("uh huh yeah ok", True, InterruptDecision.IGNORE),  # Multiple backchannels
        ("tell me more", True, InterruptDecision.INTERRUPT),  # Meaningful content
        ("what is that", True, InterruptDecision.INTERRUPT),  # Question
    ]
    
    print("BACKCHANNEL DETECTION TEST RESULTS")
    print()
    
    passed = 0
    failed = 0
    
    for transcript, agent_speaking, expected in test_cases:
        result = detector.analyze(transcript, agent_speaking=agent_speaking)
        status = "PASS" if result.decision == expected else "FAIL"
        
        if result.decision == expected:
            passed += 1
        else:
            failed += 1
        
        state = "SPEAKING" if agent_speaking else "SILENT"
        print(f"{status} | Agent: {state:8} | Input: {transcript:25} | "
              f"Expected: {expected.name:10} | Got: {result.decision.name}")
    
    print()
    print(f"RESULTS: {passed} passed, {failed} failed out of {len(test_cases)} tests")
    
    if failed > 0:
        print("\n Some tests failed! Review the detection logic.")
        return False
    else:
        print("\n All tests passed! Backchannel detection is working correctly.")
        return True


def test_custom_config():
    """Test custom configuration."""
    print("CUSTOM CONFIGURATION TEST")
    
    # Create custom config
    config = InterruptionConfig()
    config.add_ignore_word("gotcha")
    config.add_interrupt_word("cancel")
    
    detector = BackchannelDetector(config)
    
    # Test custom words
    result1 = detector.analyze("gotcha", agent_speaking=True)
    result2 = detector.analyze("cancel", agent_speaking=True)
    
    print(f"Custom ignore word 'gotcha': {result1.decision.name} (expected: IGNORE)")
    print(f"Custom interrupt word 'cancel': {result2.decision.name} (expected: INTERRUPT)")
    
    assert result1.decision == InterruptDecision.IGNORE, "Custom ignore word failed"
    assert result2.decision == InterruptDecision.INTERRUPT, "Custom interrupt word failed"
    
    print("\n Custom configuration working correctly!")
    return True


def test_performance():
    """Test detection performance."""
    import time
    
    print("PERFORMANCE TEST")
    
    detector = BackchannelDetector()
    
    test_inputs = ["yeah", "ok", "stop", "yeah but wait", "tell me more about that"]
    iterations = 1000
    
    start = time.perf_counter()
    for _ in range(iterations):
        for inp in test_inputs:
            detector.analyze(inp, agent_speaking=True)
    elapsed = time.perf_counter() - start
    
    total_ops = iterations * len(test_inputs)
    ops_per_sec = total_ops / elapsed
    avg_time_ms = (elapsed / total_ops) * 1000
    
    print(f"Total operations: {total_ops}")
    print(f"Total time: {elapsed:.3f}s")
    print(f"Operations/second: {ops_per_sec:.0f}")
    print(f"Average time per detection: {avg_time_ms:.3f}ms")
    
    if avg_time_ms < 1.0:
        print("\n Performance is excellent! Sub-millisecond detection.")
    else:
        print("\n Performance may need optimization.")
    
    return avg_time_ms < 10.0  # Should be under 10ms


def main():
    """Run all tests."""
    print("\n BACKCHANNEL DETECTION TEST SUITE\n")
    
    all_passed = True
    
    try:
        all_passed &= test_backchannels()
        all_passed &= test_custom_config()
        all_passed &= test_performance()
    except Exception as e:
        print(f"\n Test error: {e}")
        all_passed = False
    
    if all_passed:
        print(" ALL TESTS PASSED!")
    else:
        print(" SOME TESTS FAILED!")
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
