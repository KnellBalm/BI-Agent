# T1: Tableau Meta JSON Schema Design

**Status**: in_progress
**Priority**: P0
**Assigned**: Claude
**Estimated**: 3-4 hours

## Objectives

1. Define Meta JSON schema for Tableau metadata
2. Extend TableauMetadataEngine with to_meta_json() method
3. Add create_empty_meta() static method
4. Test extraction from existing .twb files

## Subtasks

- [ ] Create tableau_meta_schema.py with schema classes
- [ ] Implement TableauMetaJSON data structure
- [ ] Add to_meta_json() conversion method
- [ ] Add create_empty_meta() factory method
- [ ] Test with tmp/test.twb
- [ ] Verify JSON schema validity

## Files

- `backend/agents/bi_tool/tableau_meta_schema.py` (NEW)
- `backend/agents/bi_tool/tableau_metadata.py` (UPDATE)

## Acceptance Criteria

- Meta JSON schema includes: datasources, fields, worksheets, visuals
- Conversion from .twb XML to Meta JSON works
- Empty template generation works
- All tests pass
