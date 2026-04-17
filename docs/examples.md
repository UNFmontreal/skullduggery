# Real-World Examples

Practical examples for common use cases with skullduggery.

## Scenario 1: Quick Test on Single Participant

You have a large dataset and want to verify defacing works before processing everything.

```bash
cd /mnt/bids_data
skullduggery . --participant-label 01 --report-dir ./test_reports
```

**What this does:**
- Processes only participant `sub-01`
- Generates HTML reports for visual inspection
- Helps identify any issues before full batch

**Output to check:**
- `./test_reports/` - Open in browser to verify mask quality

---

## Scenario 2: Process Specific Cohort by Sessions

You have a longitudinal study and need to process only baseline and follow-up sessions.

```bash
skullduggery /data/my_study \
  --session-label 01 02 \
  --report-dir ./reports_cohort1 \
  --save-all-masks
```

**What this does:**
- Processes only sessions 01 (baseline) and 02 (follow-up)
- Saves masks for all images (not just reference)
- Creates visual reports for QA

**Directory structure processed:**
- `sub-001/ses-01/anat/`
- `sub-001/ses-02/anat/`
- `sub-002/ses-01/anat/`
- `sub-002/ses-02/anat/`
- etc.

---

## Scenario 3: Pediatric Data with Age-Based Templates

Your dataset includes infants and children. Use age-appropriate templates with default age fallback.

```bash
skullduggery /data/pediatric_dataset \
  --template MNIInfant:cohort-06m09m \
  --default-age 7.5:months \
  --report-dir ./peds_reports
```

**What this does:**
- Uses 6-9 month infant template
- Falls back to 7.5 months for participants with missing age data
- Ensures proper registration for pediatric brains

**Note:** For datasets with mixed ages, you may want to pre-filter:
```bash
# Only process 6-12 month old infants
skullduggery /data/pediatric_dataset \
  --template MNIInfant:cohort-06m09m \
  --participant-label infant_001 infant_003 infant_005
```

---

## Scenario 4: Processing Only Specific Image Types

Your dataset has both T1w and T2w images, but you only want to deface T1w.

```bash
skullduggery /data/multi_contrast_study \
  --other-bids-filters '{"suffix": "T1w", "datatype": "anat"}' \
  --report-dir ./t1w_only_reports
```

**What this does:**
- Ignores T2w and other contrasts
- Only defaces T1w-weighted images
- Uses T1w as reference for registration

---

## Scenario 6: DataLad-Managed Dataset with Git-Annex

Track defaced status in git-annex metadata for reproducibility.

```bash
cd /data/my_datalad_dataset
skullduggery . \
  --participant-label 01 02 03 \
  --datalad \
  --report-dir ./reports
```

**What this does:**
- Defaces images
- Updates git-annex metadata showing defacing operation
- Commits changes to your DataLad dataset

**Check the results:**
```bash
git log --oneline | head
# Should show a commit like:
# a1b2c3d defaced sub-01, sub-02, sub-03
```

---

## Scenario 7: Force Re-indexing After Dataset Updates

You added new participants/scans to an existing BIDS dataset.

```bash
skullduggery /data/growing_dataset \
  --force-reindex \
  --participant-label 04 05 06
```

**Why this matters:**
- pyBIDS caches database metadata
- Without `--force-reindex`, new files may not be detected
- Use this after adding files to ensure complete processing

---

## Scenario 8: Batch Processing with Filtering

Process multiple participant groups with different templates.

**Adult group (use MNI152):**
```bash
skullduggery /data/combined_study \
  --participant-label adult_001 adult_002 adult_003 \
  --template MNI152NLin2009cAsym \
  --report-dir ./reports_adult
```

**Pediatric group (use MNIInfant):**
```bash
skullduggery /data/combined_study \
  --participant-label child_001 child_002 child_003 \
  --template MNIInfant:cohort-12m24m \
  --report-dir ./reports_pediatric
```

---

## Scenario 9: Quality Assurance Review

Generate comprehensive reports for all participants before archiving.

```bash
skullduggery /data/dataset \
  --save-all-masks \
  --report-dir ./final_QA_reports \
  --debug info
```

**Outputs to review:**
- `./final_QA_reports/` - View HTML reports
- Check: Were all participants processed? Mask quality good?
- Look for any warnings in debug output

**Generate summary:**
```bash
ls ./final_QA_reports/sub-*/ | wc -l
# Count how many Subject reports were generated
```

---

## Scenario 10: Using External Filter Configuration

For reproducibility, store BIDS filters in version control.

**Create `defacing_filters.json`:**
```json
{
  "suffix": "T1w",
  "datatype": "anat",
  "extension": ".nii.gz"
}
```

**Use in command:**
```bash
skullduggery /data/dataset \
  --other-bids-filters ./defacing_filters.json \
  --report-dir ./reports
```

**Advantages:**
- Reproducible
- Version-controlled
- Can be documented in your study protocol

---

## Scenario 11: Processing with Debug Output

Troubleshoot issues with verbose logging.

```bash
DEBUG=1 skullduggery /data/problematic_dataset \
  --participant-label 01 \
  --debug debug \
  2>&1 | tee ./defacing_debug.log
```

**What this captures:**
- Full debug logs to both console and file
- Helps identify registration issues
- Can be attached when reporting problems

---

## Scenario 12: Resuming Failed Processing

If processing was interrupted, rerun the same command to process only affected participants.

```bash
# Original command interrupted
skullduggery /data/dataset \
  --participant-label 01 02 03 04 05 \
  --report-dir ./reports

# Rerun with only remaining participants
skullduggery /data/dataset \
  --participant-label 04 05 \
  --report-dir ./reports
```

**Check what was completed:**
```bash
ls ./reports/sub-01 ./reports/sub-02 ./reports/sub-03  # Complete
# These exist, so 01-03 were successful
```

---

## Post-Processing: Verification Scripts

After running skullduggery, verify all participants were processed:

```bash
# Count expected defaced images
find /data/dataset/derivatives -name "*_defaced.nii.gz" | wc -l

# List any failed participants
for i in $(seq -f "%02g" 1 30); do
  if [ ! -f "/data/dataset/derivatives/sub-$i/anat/*_defaced.nii.gz" ]; then
    echo "sub-$i: MISSING"
  fi
done
```

---

## Tips for Large-Scale Processing

1. **Process in batches:**
   ```bash
   # Process 10 at a time to monitor progress
   skullduggery /data/dataset --participant-label 01-10 --report-dir ./batch_1
   skullduggery /data/dataset --participant-label 11-20 --report-dir ./batch_2
   ```

2. **Use screen or tmux for long runs:**
   ```bash
   screen -S defacing
   skullduggery /data/large_dataset --report-dir ./reports
   # Detach with Ctrl-A Ctrl-D
   ```

3. **Monitor progress:**
   ```bash
   while true; do
     count=$(find ./reports -type d -name "sub-*" | wc -l)
     echo "Processed: $count participants"
     sleep 60
   done
   ```

4. **Generate summary report:**
   ```bash
   echo "=== Defacing Summary ===" > summary.txt
   echo "Total reports: $(ls ./reports/sub-* -d | wc -l)" >> summary.txt
   echo "Completed at: $(date)" >> summary.txt
   ```
