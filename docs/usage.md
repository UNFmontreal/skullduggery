# Usage Guide

Skullduggery is a command-line tool for automated defacing of anatomical MRI images in BIDS datasets. This guide covers how to use the tool from the command line.

## Installation

### Basic Installation
```bash
pip install skullduggery
```

### With Optional Features
For git-annex metadata tracking (DataLad integration):
```bash
pip install skullduggery[datalad]
```

## Basic Usage

### Minimal Command
To deface all anatomical images in a BIDS dataset:

```bash
skullduggery /path/to/bids/dataset
```

This command:
- Processes all participants in the dataset
- Uses the default template (MNI152NLin2009cAsym)
- Saves defaced images alongside originals
- Processes T1w reference images by default

### What Gets Processed

By default, skullduggery:
- **Searches for**: All anatomical images (anat datatype)
- **Reference series**: Uses T1w weighted images as the registration reference
- **Output**: Saves defaced images with `_defaced` suffix

## Common Command-Line Options

### Filter Participants and Sessions

**Process specific participants:**
```bash
skullduggery /path/to/bids/dataset --participant-label 01 02 05
```

**Process specific sessions:**
```bash
skullduggery /path/to/bids/dataset --session-label 01 02
```

**Combine filters:**
```bash
skullduggery /path/to/bids/dataset \
  --participant-label 01 02 03 \
  --session-label 01
```

### Template Selection

**Use different registration template:**
```bash
skullduggery /path/to/bids/dataset --template MNI152NLin6Asym
```

**For pediatric data (age-specific templates):**
```bash
skullduggery /path/to/bids/dataset --template MNIInfant:cohort-07m09m
```

**When participants.tsv lacks age data:**
```bash
skullduggery /path/to/bids/dataset \
  --template MNIInfant:cohort-06m09m \
  --default-age 6:months
```

### Output Options

**Save masks for all defaced series:**
```bash
skullduggery /path/to/bids/dataset --save-all-masks
```

By default, only the mask for the reference series is saved. Use this flag to save masks for all defaced images.

**Generate HTML reports with visualizations:**
```bash
skullduggery /path/to/bids/dataset \
  --report-dir ./defacing_reports
```

Creates an HTML report showing:
- Defacing masks overlaid on images
- Before/after mosaic views
- Processing status for each image

## Image Selection Filters

### Using BIDS Filters

**Process only T2w weighted images:**
```bash
skullduggery /path/to/bids/dataset \
  --other-bids-filters '{"suffix": "T2w", "datatype": "anat"}'
```

**Process specific anatomical contrasts:**
```bash
skullduggery /path/to/bids/dataset \
  --other-bids-filters '{"suffix": ["T1w", "T2w"], "datatype": "anat"}'
```

**Use filter from JSON file:**
```bash
skullduggery /path/to/bids/dataset \
  --other-bids-filters /path/to/filters.json
```

Where `filters.json` contains:
```json
{
  "suffix": "T1w",
  "datatype": "anat"
}
```

### Reference Series Filters

**Change reference series for registration:**
```bash
skullduggery /path/to/bids/dataset \
  --ref-bids-filters '{"suffix": "T2w", "datatype": "anat"}'
```

The reference series determines which image is used for template registration. All other anatomical images are defaced using the transformed mask.

## Advanced Options

### Force BIDS Reindexing

If you've recently added files to your BIDS dataset:
```bash
skullduggery /path/to/bids/dataset --force-reindex
```

This forces pyBIDS to re-scan the directory instead of using cached metadata.

### DataLad Integration

**Update distribution restrictions metadata:**
```bash
skullduggery /path/to/bids/dataset --datalad
```

This option:
- Updates git-annex metadata to mark files as defaced
- Commits changes automatically
- Useful for DataLad-managed repositories

### Git-annex Sensitive Selection

**Select series using git-annex metadata:**
```bash
skullduggery /path/to/bids/dataset --deface-sensitive
```

Selects images marked as sensitive in git-annex metadata.

### Debug Output

**Enable debug logging:**
```bash
skullduggery /path/to/bids/dataset --debug info
```

Enables verbose logging to help troubleshoot issues. Use one of: `debug`, `info`, `warning`, `error`.

## Exit Codes

- **0**: All participants processed successfully
- **1**: One or more errors occurred during processing

Check the log output to identify specific failures.

## Tips and Best Practices

1. **Test first**: Try on a single participant before processing the whole dataset
   ```bash
   skullduggery /path/to/bids/dataset --participant-label 01
   ```

2. **Generate reports**: Always create visual reports for quality assurance
   ```bash
   skullduggery /path/to/bids/dataset --report-dir ./defacing_reports
   ```

3. **Back up before running**: Ensure you have a backup before defacing in-place modifications

4. **Use participant labels without prefix**: The `sub-` prefix is optional
   ```bash
   # These are equivalent:
   skullduggery /path/to/bids/dataset --participant-label 01
   skullduggery /path/to/bids/dataset --participant-label sub-01
   ```

5. **Process sessions consistently**: If using longitudinal data, process all sessions
   ```bash
   skullduggery /path/to/bids/dataset --session-label 01 02 03
   ```

## Getting Help

**View all available options:**
```bash
skullduggery --help
```

**Check version:**
```bash
python -c "import skullduggery; print(skullduggery.__version__)"
```
