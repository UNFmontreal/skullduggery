# Getting Started

Welcome to Skullduggery! This guide will get you up and running quickly.

## What is Skullduggery?

Skullduggery is a command-line tool that automatically removes identifiable facial features from anatomical MRI images in your BIDS dataset while preserving brain tissue. This protects participant privacy in neuroimaging research.

## Installation

```bash
pip install skullduggery
```

## Your First Deface

Try this command on a small test group first:

```bash
skullduggery /path/to/bids/dataset --participant-label 01 --report-dir ./test_reports
```

Then open the HTML reports to verify the results:
```bash
open ./test_reports/sub-01/index.html  # macOS
xdg-open ./test_reports/sub-01/index.html  # Linux
start ./test_reports/sub-01/index.html  # Windows
```

## Next Steps

- **See all options:** Read the [Usage Guide](usage.md)
- **Look up a specific flag:** Check the [Command Reference](command-reference.md)
- **Real-world workflows:** Browse [Examples](examples.md)
- **Troubleshooting:** See [Usage Guide - Tips and Best Practices](usage.md#tips-and-best-practices)

## Common Commands

| Goal | Command |
|------|---------|
| Process everyone | `skullduggery /path/to/dataset` |
| Process specific people | `skullduggery /path/to/dataset --participant-label 01 02 03` |
| Specific sessions only | `skullduggery /path/to/dataset --session-label 01` |
| Generate visual reports | `skullduggery /path/to/dataset --report-dir ./reports` |
| Pediatric data | `skullduggery /path/to/dataset --template MNIInfant:cohort-06m09m` |
| Get help | `skullduggery --help` |

## Structure

The documentation is organized by use case:

1. **Getting Started** (this page) - Quick overview
2. **Usage Guide** - Detailed explanation of all command-line options
3. **Command Reference** - Quick lookup table for all flags
4. **Examples** - 12 real-world scenarios with complete commands

## Key Concepts

### BIDS Dataset
Skullduggery works with BIDS-formatted neuroimaging datasets. Your dataset should have this structure:
```
dataset/
  sub-001/
    anat/
      sub-001_T1w.nii.gz
      sub-001_T1w.json
  sub-002/
    anat/
      sub-002_T1w.nii.gz
      ...
```

### Defacing Mask
Skullduggery creates a mask defining which voxels to remove. It then applies this mask to all anatomical images in each session.

### Reference Series
By default, T1w images are used as the reference to register the template. If your dataset uses different references, you can customize with `--ref-bids-filters`.

### Templates
Skullduggery registers images to a template space to define the face mask. Common choices:
- `MNI152NLin2009cAsym` (default, adults)
- `MNI152NLin6Asym` (alternative adult template)
- `MNIInfant:cohort-06m09m` (6-9 month infants)
- `MNIInfant:cohort-12m24m` (12-24 month infants)

## Troubleshooting

**Command not found:**
```bash
# Verify installation
pip list | grep skullduggery
# Reinstall if needed
pip install --upgrade skullduggery
```

**Permission issues:**
```bash
# Ensure you can read the dataset
ls /path/to/dataset  # Should list sub-* folders
```

**See what it's doing:**
```bash
# Enable debug output
DEBUG=1 skullduggery /path/to/dataset --participant-label 01 --debug debug
```

## Getting Help

- **View all options:** `skullduggery --help`
- **Browse documentation:** Start with [Usage Guide](usage.md)
- **Search for specific topic:** Use [Command Reference](command-reference.md)
- **Need an example?** Check [Examples](examples.md)
