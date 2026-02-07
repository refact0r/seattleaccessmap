# Access to Everyday Life

<aside>
💡

*Can everyone move, navigate, and belong?*

</aside>

## Introduction

Cities shape how people move, navigate, and participate in everyday life — but the ability to move freely is not equally distributed. Sidewalk design, curb ramps, surface quality, and obstacles can create friction that affects safety, independence, and belonging for many people.

The **Project Sidewalk Seattle Accessibility Dataset** contains crowdsourced observations of sidewalk conditions across Seattle, including accessibility barriers such as surface problems, obstacles, missing curb ramps, and other design challenges. Each record includes geographic coordinates, neighborhood information, severity ratings, and whether a barrier is temporary or permanent.

As a Datathon participant, your team is challenged to explore **access to everyday life**: Who can move independently? Where does movement slow down or become unsafe? How do design assumptions shape inclusion and exclusion in urban spaces?

This Datathon is your chance to transform real-world accessibility data into actionable insights — revealing mobility gaps, highlighting inequities in the built environment, and proposing data-driven solutions for more inclusive cities.

---

## Tasks

Your task is to answer one or more of the following questions, or any other question that sparks curiosity in you and your team regarding accessibility, movement, and urban design.

### Machine Learning / Predictive Modeling

Teams interested in ML may attempt tasks such as:

- Predict **severity of accessibility issues** based on location and contextual features
- Classify **types of accessibility barriers** (e.g., surface problem, obstacle, curb ramp issue)
- Identify **high-risk accessibility hotspots** using clustering or spatial modeling
- Predict **where future accessibility problems are likely to occur**
- Build models that estimate **mobility friction scores** across neighborhoods
- Cluster neighborhoods based on **accessibility patterns and infrastructure conditions**

### Data Analytics and Data Visualization

The following questions can be attempted by analytics and visualization teams:

- Which neighborhoods contain the **highest number of accessibility barriers**?
- Where are the **most severe sidewalk accessibility problems** located?
- How do accessibility challenges vary **block by block or neighborhood by neighborhood**?
- What types of barriers occur most frequently across Seattle?
- Map **mobility friction zones** where movement may be slow or unsafe
- Compare **temporary vs. permanent barriers** across geographic areas
- Build an **Accessibility Score** or index for different neighborhoods

---

## Download the Dataset

[Project Sidewalk Seattle Accessibility Dataset](https://drive.google.com/file/d/1S3sknUHnd1ewnLyJayfSTpalS4FjMi95/view?usp=sharing)

More info about the dataset:

[Harvard Dataverse - Project Sidewalk](https://dataverse.harvard.edu/dataset.xhtml?persistentId=doi:10.7910/DVN/YOTY6A)

---

## Submission Requirements

- **Format:** Submit your work in a universally acceptable format (`.doc`, `.pdf`, `.md`, URL) along with a link to your code repository (e.g., GitHub). If you create a predictive model, include model accuracy and margin of error.
- **Focus:** We recommend focusing on a maximum of 3 tasks. Quality over quantity.
- **Important:** All work must be created during the DubsTech Datathon hours. Work submitted outside these hours will not be considered.

<aside>
💡

**Submission Form:**

</aside>

---

### Dataset Columns

The dataset includes the following columns:

- `type` – GeoJSON feature type
- `geometry/type` – Geometry format (Point)
- `geometry/coordinates/0` – Longitude
- `geometry/coordinates/1` – Latitude
- `properties/attribute_id` – Unique identifier for each accessibility observation
- `properties/label_type` – Type of accessibility issue (e.g., SurfaceProblem, Obstacle, CurbRamp)
- `properties/neighborhood` – Neighborhood name
- `properties/severity` – Severity rating of the accessibility issue
- `properties/is_temporary` – Whether the issue is temporary or permanent

**Recommended preprocessing:**

- Convert coordinates into geospatial maps or spatial features
- Aggregate data by **neighborhood or geographic clusters**
- Compute **Accessibility Density** (barriers per area or per route)
- Create derived features such as **mobility friction score** or **severity averages**
- Join with external datasets (e.g., demographics, transit access, infrastructure data) for equity analysis
