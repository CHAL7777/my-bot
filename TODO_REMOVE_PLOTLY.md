# TODO: Remove Plotly from Project

## Objective
Remove plotly and kaleido dependencies from the project as they are no longer needed.

## Steps to Complete

### Step 1: Remove plotly and kaleido from requirements.txt
- [x] Remove `plotly>=5.20.0` line
- [x] Remove `kaleido>=0.2.1` line

### Step 2: Modify app/handlers/progress.py
- [x] Remove plotly imports (`plotly.graph_objects` and `plotly.io`)
- [x] Remove unused imports (`from io import BytesIO` if no longer needed)
- [x] Replace `generate_performance_graph` function with text-based alternative
- [x] Update callback handler to use new function


- [x] Plan approved by user
- [x] In progress
- [ ] Completed

