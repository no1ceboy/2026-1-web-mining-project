# Member 4: Aspect-based opinion analysis

## Purpose

This workstream identifies the game aspects discussed in review text, determines whether the reviewer expresses a positive or negative view of each aspect, and checks extraction quality against human labels. Aspect-level sentiment is separate from Steam's overall recommendation vote.

## Current status

The repository contains a ten-category aspect guide, a 50-review development batch, a rule-based extractor, an evaluator, and a proposed opinion feature for LightGCN. The annotation batch has 16 negative recommendations and 15 reviews assigned for independent second labeling.

Human labels and independent second labels have not been completed. The machine-generated annotation draft is not ground truth. The pretrained aspect-based sentiment analysis model has been implemented but not run. The current rule-based outputs and opinion profiles are exploratory and have no validated precision, recall, or F1. See [the validation status report](../../../outputs/opinion_validation_v0.md).

## Annotation rules

For each review, record the aspect discussed, the sentiment toward that aspect, and an exact supporting span from the review. Do not infer aspect sentiment from Steam's overall vote. Keep sarcasm, uncertainty, and mixed sentiment visible in notes rather than silently converting them to a simple label.

The first 50 reviews are a development batch for the taxonomy and annotation process. Ask a second annotator to label the shared subset independently before comparing labels. Review disagreements and agree on final labels. Keep a separate evaluation sample; do not score an extractor on examples used to define its rules.

## Opinion features

The proposed compatibility feature uses only text available before each recommendation cutoff. It weights game opinions by the aspects a user has discussed and combines the result with a normalized LightGCN score. This feature is a proposal until the annotations are validated, the cutoff-specific input is complete, and Member 3 confirms the score contract.

Current pilot profiles cover 14 of 22 validation users and 10 of 23 test users. They are built from only 85 candidate texts and a lexicon extractor that has not been validated. Do not describe the coverage file as a recommendation result.

## Remaining work

1. Correct the machine-generated draft against the source reviews and annotation guide; save human work under a human annotator ID.
2. Have a teammate independently label the overlap set, then reconcile disagreements.
3. Run both the lexicon baseline and a pretrained ABSA model against held-out human labels.
4. Report aspect and sentiment metrics, evidence-span errors, and coverage with denominators.
5. Export opinion candidates for each cutoff and rerun the opinion-augmented LightGCN comparison only after validation.
