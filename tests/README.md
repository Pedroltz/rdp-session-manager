# RDP Session Manager - Test Suite Documentation

Complete unit test suite for RDP Session Manager with 109 tests covering the system's core modules.

## Overview

- **Total Tests**: 109
- **Test Files**: 6
- **Framework**: Python `unittest`
- **Success Rate**: 100%

## File Structure

```
tests/
├── README.md                  # This file
├── run_tests.sh              # Script to run tests
├── test_backup.py            # 20 tests - Backup system
├── test_config.py            # 17 tests - Configuration
├── test_logger.py            # 25 tests - Logging and audit
├── test_session_monitor.py   # 23 tests - Session monitoring
├── test_user_manager.py      # 14 tests - User management
└── test_validator.py         # 20 tests - Input validation
```

## Test Files

### test_user_manager.py (14 tests)

Tests `src/core/user_manager.py` - RDP user management.

**Main Tests**:
- RDPUser serialization/deserialization
- Username validation
- UID and port generation
- RDP group verification
- Default values (enabled, is_superuser)

**Importance**: Ensures integrity in user creation and management.

---

### test_validator.py (20 tests)

Tests `src/utils/validator.py` - System input validation.

**Main Tests**:
- Username validation (pattern, size, reserved)
- Password validation (complexity, confirmation)
- Port validation (range 1024-65535)
- Desktop environment validation
- Home directory validation (security)
- Path sanitization (injection prevention)

**Importance**: Security and command injection prevention.

---

### test_session_monitor.py (23 tests)

Tests `src/core/session_monitor.py` - RDP session monitoring.

**Main Tests**:
- Active session detection
- Session duration calculation
- Session search by user
- Server IP detection
- Session termination
- System statistics (CPU, RAM, disk)
- Port status verification

**Importance**: Real-time monitoring and diagnostics.

---

### test_config.py (17 tests)

Tests `src/core/config.py` - INI configuration system.

**Main Tests**:
- config.ini creation and loading
- Configuration persistence
- Default values
- Corrupted file recovery
- Multiple sections and keys
- RDP port validation

**Importance**: Reliable configuration persistence.

---

### test_logger.py (25 tests)

Tests `src/utils/logger.py` - Logging and audit system.

**Main Tests**:
- Event logging in JSON and text
- Event filtering by user
- Logger setup (console and file)
- Log rotation (10MB, 5 backups)
- Handlers without duplication
- Fallback to home directory

**Importance**: Audit, debugging and traceability.

---

### test_backup.py (20 tests)

Tests `src/utils/backup.py` - Configuration backup system.

**Main Tests**:
- Backup creation and restoration
- Backup listing and sorting
- Old backup cleanup
- Configuration import/export
- Data integrity (roundtrip)
- Multiple backups per user

**Importance**: Disaster recovery and migration.

---

## How to Run

### Method 1: Professional Script (Recommended)

```bash
./run_tests.sh
```

Output with colors, statistics and formatted summary.

### Method 2: Python unittest

```bash
# All tests
python3 -m unittest discover tests/ -v

# Specific file
python3 -m unittest tests.test_validator -v

# Specific class
python3 -m unittest tests.test_user_manager.TestUserManager -v

# Individual test
python3 -m unittest tests.test_validator.TestValidator.test_validate_username_valid -v
```

### Method 3: Run Directly

```bash
python3 tests/test_validator.py -v
```

## Test Structure

```python
import unittest
from unittest.mock import Mock, patch

class TestModule(unittest.TestCase):
    """Test description"""

    def setUp(self):
        """Executed before each test"""
        self.obj = SomeClass()

    def tearDown(self):
        """Executed after each test"""
        pass

    def test_functionality(self):
        """Test description"""
        # Arrange
        input_data = "test"

        # Act
        result = self.obj.method(input_data)

        # Assert
        self.assertEqual(result, expected)
```

## Testing Practices

### Isolation
- Each test is independent
- setUp/tearDown for fixtures
- Temporary directories for I/O
- No dependencies between tests

### Mocking
- `unittest.mock` for external dependencies
- `@patch` to replace system calls
- Avoids side effects

### Coverage
- Normal cases (happy path)
- Error cases (sad path)
- Edge cases and boundary values
- Negative tests

### Naming
- `test_<functionality>_<scenario>()`
- Descriptive names
- Explanatory docstrings

## Debugging Failing Tests

### View Detailed Output

```bash
python3 -m unittest tests.test_validator.TestValidator.test_validate_username_valid -v
```

### Add Prints

```python
def test_something(self):
    result = function_under_test()
    print(f"DEBUG: result = {result}")
    self.assertEqual(result, expected)
```

### Use pdb (Python Debugger)

```python
import pdb

def test_something(self):
    result = function_under_test()
    pdb.set_trace()  # Pause here
    self.assertEqual(result, expected)
```

## Coverage Statistics

| Module | Tests | Status |
|--------|--------|--------|
| user_manager.py | 14 | Complete |
| validator.py | 20 | Complete |
| session_monitor.py | 23 | Complete |
| config.py | 17 | Complete |
| logger.py | 25 | Complete |
| backup.py | 20 | Complete |
| **TOTAL** | **109** | **100%** |

## Contributing Tests

### Adding New Tests

1. Create `tests/test_new_module.py`
2. Follow existing structure:

```python
#!/usr/bin/env python3
"""Tests for NewModule"""

import unittest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from core.new_module import NewClass

class TestNewClass(unittest.TestCase):
    """Test NewClass"""

    def test_something(self):
        """Test description"""
        # your tests here
        pass
```

3. Run: `python3 -m unittest tests.test_new_module -v`

### Checklist

- [ ] File created at `tests/test_<module>.py`
- [ ] Docstrings in all functions
- [ ] setUp/tearDown if needed
- [ ] Normal and error cases
- [ ] Edge cases tested
- [ ] All tests passing

## Benefits

**Regression Prevention**: Changes don't break existing code

**Safe Refactoring**: Changes with confidence

**Living Documentation**: Tests show correct usage

**Fast Debugging**: Failures indicate exactly the problem

**Better Design**: Testable code is better structured

## Resources

- [Python unittest](https://docs.python.org/3/library/unittest.html)
- [unittest.mock](https://docs.python.org/3/library/unittest.mock.html)
- [Test-Driven Development](https://en.wikipedia.org/wiki/Test-driven_development)

---

**Version**: 0.2.2
**Last Updated**: 2025-10-24
**Tests**: 109/109 passing
