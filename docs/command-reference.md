# Command Reference

Complete reference for all skullduggery command-line options.

## Syntax

```
skullduggery <BIDS_PATH> [OPTIONS]
```

## Required Arguments

| Argument | Description |
|----------|-------------|
| `BIDS_PATH` | Path to the root directory of your BIDS dataset |

## Optional Arguments

### Participant & Session Filtering

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--participant-label` | space-separated list | ALL | Specific participant IDs to process (e.g., `01 02 03`). Prefix `sub-` is optional. |
| `--session-label` | space-separated list | ALL | Specific session IDs to process (e.g., `01 02`). Prefix `ses-` is optional. |

### Template & Registration

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--template` | string | `MNI152NLin2009cAsym` | TemplateFlow template for registration. Use pediatric templates like `MNIInfant:cohort-06m09m` for age-specific templates. |
| `--default-age` | string | none | Default age when participants.tsv lacks age data. Format: `<value>:<unit>` (e.g., `6:months`, `2:years`). |

### Image Selection

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--ref-bids-filters` | JSON or file path | `{"suffix": "T1w", "datatype": "anat"}` | BIDS filters to select the reference series for registration. Can be inline JSON or path to JSON file. |
| `--other-bids-filters` | JSON or file path | `[{"datatype": "anat"}]` | BIDS filters to select all images to deface. Can be inline JSON or path to JSON file. |
| `--deface-sensitive` | flag | false | Select only series marked as sensitive in git-annex metadata. |

### Output Options

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--save-all-masks` | flag | false | Save defacing masks for all defaced series. Default saves masks only for reference series. |
| `--report-dir` | directory path | none | Write HTML reports with defacing visualizations to this directory. |

### Processing Options

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--force-reindex` | flag | false | Force pyBIDS to re-scan the dataset instead of using cached metadata. Use if you recently added files. |
| `--datalad` | flag | false | Update git-annex metadata with defacing information and commit changes. Requires DataLad installation. |

### Debugging

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--debug` | string | `info` | Set logging level. Options: `debug`, `info`, `warning`, `error` |

## Filter Format

### JSON Format for BIDS Filters

Filters use pybids syntax. Common options:

#### By Suffix
```json
{"suffix": "T1w"}
{"suffix": ["T1w", "T2w"]}
```

#### By Datatype
```json
{"datatype": "anat"}
```

#### By Extension
```json
{"extension": ".nii.gz"}
```

#### By Custom Label
```json
{"label": "value"}
```

#### Combined Filters
```json
{
  "suffix": "T1w",
  "datatype": "anat",
  "extension": ".nii.gz"
}
```

### Inline vs File-based

**Inline JSON:**
```bash
skullduggery /path/to/dataset \
  --other-bids-filters '{"suffix": "T1w"}'
```

**From file:**
```bash
skullduggery /path/to/dataset \
  --other-bids-filters /path/to/filters.json
```

## Age Format

When using `--default-age`, format is `VALUE:UNIT`:

| Unit | Examples |
|------|----------|
| `days` | `1:days`, `30:days` |
| `weeks` | `2:weeks`, `52:weeks` |
| `months` | `6:months`, `18:months` |
| `years` | `5:years`, `80:years` |

## Exit Codes

| Code | Meaning |
|------|---------|
| `0` | Success - all participants processed |
| `1` | Failure - one or more errors occurred |

## Examples

### Basic
```bash
skullduggery /data/bids_dataset
```

### With participant filtering
```bash
skullduggery /data/bids_dataset --participant-label 01 02 03
```

### With reports
```bash
skullduggery /data/bids_dataset --report-dir ./reports
```

### Full options
```bash
skullduggery /data/bids_dataset \
  --participant-label 01 02 03 \
  --session-label 01 \
  --template MNI152NLin6Asym \
  --save-all-masks \
  --report-dir ./reports \
  --debug debug
```

## Environment Variables

| Variable | Effect |
|----------|--------|
| `DEBUG` | When set to any truthy value, enables debug logging |

Example:
```bash
DEBUG=1 skullduggery /path/to/dataset
```

## Tips

- Use `--help` to see the full help message
- Participant/session labels don't need the `sub-`/`ses-` prefix
- JSON filters can be tested with pybids directly
- Use `-f/--force-reindex` if you've recently modified your dataset
