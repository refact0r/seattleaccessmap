# DubsTech Datathon Project: City Accessibility Analysis

## Overview

Hackathon project using the **Project Sidewalk Seattle Accessibility Dataset** (~82k crowdsourced observations of sidewalk conditions). The goal is to both analyze the data, create a map visualization, and most importantly to build a routing tool that finds alternative accessible paths that minimize exposure to accessibility barriers for people with mobility challenges.

Hackathon prompt: `reference/access-to-everyday-life.md`. We're deviating a little from the prompt's questions (we just want to make a cool project) but still addressing the core themes.

## Dataset

- Location: 'data/data_clean.csv' ('data/data.csv' is the raw dataset)
- Records: 79,722 (dropped 2,251 rows with missing severity ratings)
- Columns:
  - `lon`, `lat` - coordinates
  - `id` - unique observation ID
  - `label` - 7 types: `CurbRamp`, `NoCurbRamp`, `NoSidewalk`, `Obstacle`, `SurfaceProblem`, `Other`
  - `neighborhood`: 50 neighborhoods of Seattle
  - `severity`: 1-5 scale (guaranteed to be present in the cleaned dataset)
  - `is_temporary`: boolean (~771 are TRUE, rest FALSE)
