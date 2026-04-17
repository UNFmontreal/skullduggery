# Getting Started

Skullduggery removes identifiable facial features from anatomical MRI images while preserving brain tissue, protecting privacy in neuroimaging research.

## Install

```bash
pip install skullduggery
```

## Your First Command

```bash
skullduggery /path/to/bids/dataset --participant-label 01 --report-dir ./test_reports
```

## Common Commands

| Goal | Command |
|------|---------|
| Process everyone | `skullduggery /path/to/dataset` |
| Specific participants | `skullduggery /path/to/dataset --participant-label 01 02 03` |
| Specific sessions | `skullduggery /path/to/dataset --session-label 01` |
| With reports | `skullduggery /path/to/dataset --report-dir ./reports` |
| Pediatric data | `skullduggery /path/to/dataset --template MNIInfant:cohort-06m09m` |
| All options | `skullduggery --help` |

## Next Steps

- [Usage Guide](usage.md) - All command-line options
- [Command Reference](command-reference.md) - Quick lookup
- [Examples](examples.md) - Real-world scenarios
