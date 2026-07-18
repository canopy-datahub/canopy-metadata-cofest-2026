# Canopy: AI-Assisted Metadata Generation

### CollaborationFest 2026 Project - [CoFest 2026](https://www.open-bio.org/events/bosc-2026/collaborationfest/)

This project is defined in the context of **[Canopy](https://github.com/canopy-datahub)**, an open-source platform for building FAIR-aligned scientific data hubs that support data sharing, harmonization, discovery, and reuse across research studies.

In Canopy, researchers organize and share data as studies, each consisting of one or more datasets together with structured metadata describing the study, its datasets, and related resources.
This metadata is authored using **[CEDAR](https://metadatacenter.org/)**, an open-source platform for designing and managing machine-readable metadata templates.

Creating high-quality metadata is still largely manual.
Researchers often extract information from datasets, data dictionaries, protocols, and publications, then translate it into structured metadata.
This project explores AI-assisted approaches for automating parts of that process while maintaining high-quality metadata that can be used in Canopy.
As a bonus part, we will also explore how this metadata can be used to populate and register studies in Canopy.

## Project Goals

The goal of this CoFest project is to explore reusable AI-assisted workflows for metadata generation.

As illustrated below, these workflows can use AI to extract and structure information from unstructured documents, populate CEDAR templates, and generate standards-based metadata instances.

![workflow](images/workflow.png)

Rather than building a workflow tailored to a single dataset, we encourage participants to experiment with prompting strategies, pipelines, and agentic workflows that can be reused across different studies and research domains.

Participants are encouraged to explore ideas such as:

- Designing reusable prompting strategies for metadata generation.
- Developing reusable metadata generation workflows that can be applied across studies and research domains.
- Evaluating different LLMs, tools, and prompting techniques.
- Exploring how generated metadata can be integrated into Canopy.

Before diving into the project, we'll first set up the development environment and complete a short tutorial covering the core concepts used throughout the rest of the project.

## Prerequisite — bring your own LLM
You need access to an LLM with tool/MCP support (Claude, ChatGPT, Gemini, …); we don't provide a license. Because the MCP servers are an open standard, the same prompts and servers should work across clients.

## Environment Setup

Before jumping into the tutorial and project, please complete the environment setup by following the instructions on [this page](./INSTALL.md). Once everything is set up, come back here to continue.

## Tutorial

Before starting the project, complete this short tutorial to verify that your environment is set up correctly and to become familiar with the core concepts.

In this tutorial, you'll learn the basics of creating metadata with **CEDAR**, the metadata platform used by Canopy. A **CEDAR template** defines the metadata fields to be captured (for example, title, authors, or publication date), while an **instance** is a completed metadata record created from that template.

To complete the tutorial, you'll use the **MCP (Model Context Protocol) servers** you just configured. These servers allow your LLM to interact with CEDAR and BioPortal to create, validate, visualize, and store metadata. The MCP servers used in this project are summarized below.

### MCP Servers

| MCP server | Purpose |
|------------|---------|
| [`cedar‑artifact‑mcp`](https://github.com/metadatacenter/cedar-artifact-mcp) | Create and validate CEDAR templates and metadata instances. |
| [`bioportal‑term‑mcp`](https://github.com/metadatacenter/bioportal-term-mcp) | Search BioPortal for ontology terms and controlled vocabulary values. |
| [`cedar‑artifact‑rest‑mcp`](https://github.com/metadatacenter/cedar-artifact-rest-mcp) | Upload, retrieve, and manage templates and instances on a CEDAR server. |
| [`cedar‑cee‑mcp`](https://github.com/metadatacenter/cedar-cee-mcp) | Visualize templates and instances as interactive forms using the CEDAR Embeddable Editor. |

Throughout this tutorial, you'll interact with your LLM using natural language. In most cases, the LLM will automatically choose the appropriate MCP server. If it doesn't, you can explicitly ask it to use a specific MCP based on the table above. 

1. Create a template
Ask your LLM to ceate a simple **publication metadata template**. Your template should include:

- Title
- Authors (including their ORCID identifiers)
- Publication date
- Publication type (use a controlled vocabulary linked to the [SIO "publication" term](https://bioportal.bioontology.org/ontologies/SIO?p=classes&conceptid=http%3A%2F%2Fsemanticscience.org%2Fresource%2FSIO_000087) in BioPortal)
- Keywords

Once your template is complete:

2. Validate & visaulize
Ask yout LLM to validate the generated template and then visualize it using the appropriate MCPs.
3. Generate an instance
Find any journal article and ask your LLM to populate the template for that article.
4. Visualize
Visualize the generated instance to verify that it renders correctly.
5. Upload
Upload both the template and the instance to CEDAR.
Log into your CEDAR account and verify that both artifacts were uploaded successfully.

## Project Tasks and Example Workflow

To provide a common starting point, we include a [synthetic study](data/synthetic-study) that can be used to evaluate an end-to-end AI-assisted metadata generation workflow. This workflow is only an example—you are encouraged to adapt, extend, or replace it with your own reusable approach.

### Project Task 1 — Populate the existing Canopy study template

Canopy provides a generic **Canopy Study Template** that captures the study-level metadata required for every submission. Start by retrieving this existing template from CEDAR using `cedar-artifact-rest-mcp` using the template ID provided, then generate a completed metadata instance from the provided study materials.

**Template:** [Canopy Study Template in CEDAR](https://openview.metadatacenter.org/templates/https:%2F%2Frepo.metadatacenter.org%2Ftemplates%2Faff00b59-0bb7-4e40-9437-3216e5fb0ff7)

**Template ID**:
```text
https://repo.metadatacenter.org/templates/aff00b59-0bb7-4e40-9437-3216e5fb0ff7
```

### Project Task 2 — Design a domain-specific metadata template

Create a new CEDAR template describing the metadata specific to the provided dataset. Choose appropriate field types and, where appropriate, controlled vocabulary terms from BioPortal.

### Project Task 3 — Populate your domain-specific template

Populate the template created in Task 2 using information extracted from the provided datasets and documents.

### Project Task 4 — Register the study in Canopy

Use the metadata you generated in the previous tasks to create and populate a study in Canopy. This demonstrates how AI-generated metadata can feed the complete submission workflow, from a metadata instance to a registered study.

At a high level, you will:

1. Sign in to Canopy ([production instance](https://canopy.stanford.edu/)).
2. Create a new study and populate its study-level metadata using the instance you generated in **Project Task 1**.
3. Attach the dataset(s) and any related resources from the provided study materials.
4. Review and submit the study.

For the exact steps, follow the Canopy documentation:

- **[Canopy — Submission Workflow tutorial](https://canopy.stanford.edu/tutorial?tutorial=submissionWorkflow)** — walks through creating and submitting a study.
- **[Canopy — Data Access Control tutorial](https://canopy.stanford.edu/tutorial?tutorial=dataAccessControl)** — covers configuring who can access the study and its data.

### Project Task 5 — Apply your workflow to your own data

If your team finishes the tasks above with time to spare, put your workflow to the test on **data and documents of your own choosing** — a dataset from your lab, a public dataset, a study you know well, or anything else that interests you.

The goal is to demonstrate that the workflow you built is genuinely reusable, rather than tuned to the study we provided. Concretely:

1. Select a dataset together with any accompanying documents (data dictionary, protocol, publication, README).
2. Design a metadata template for it (or reuse/adapt one from the earlier tasks).
3. Run your pipeline end-to-end to populate the template from your chosen materials.
4. Note what worked, what needed adjustment, and any gaps you had to fill by hand.

This is a great candidate for your CoFest presentation: showing the pipeline applied to your *own* data makes the demo more compelling and highlights how the approach generalizes across studies and domains.

### Project Task 6 — Evaluate your Workflow

The goal is to build a tool to evaluate the quality of the generated template and metadata.
This task is open in terms of the approach you choose. Once you complete this task, you might consider sharing your tool with other participants, so they can also evaluate the quality of their results.

## Deliverables

The primary deliverable is a reusable AI workflow and reusable knowledge that others can build upon.

Examples of useful deliverables include:

- Reusable prompts for metadata generation.
- AI workflows or pipelines that can be applied to multiple studies.
- Agentic workflows combining MCP servers and LLMs.
- Lessons learned, best practices, and common pitfalls.
- A study registered in Canopy using the generated metadata (Task 4). 
- The workflow applied to a dataset of your own choosing (Task 5).
- Your evaluation method (Task 6).

## Get Going

> 1. **🍴 Fork this repo, then clone your fork** to your machine.
> 2. **📂 Work in the `work/` folder.** Keep everything you produce there.
> 3. **⚙️ If you followed the turorial tools and servers should already be installed but if not:** — open the **👉 [setup guide](INSTALL.md)** and follow it.

## CoFest 2026 On-Site Team

| Name                   | Role            | Affiliation         | Email                                                 |
| ---------------------- | --------------- | ------------------- | ----------------------------------------------------- |
| Attila L. Egyedi       | Project Lead    | Stanford University | [egyedia@stanford.edu](mailto:egyedia@stanford.edu)   |
| Mete Akdogan           | Project Support | Stanford University | [mete@stanford.edu](mailto:mete@stanford.edu)         |
| Marcos Martínez Romero | Project Support | Stanford University | [marcosmr@stanford.edu](mailto:marcosmr@stanford.edu) |

## Links

| Resource                              | Link                                                               |
|---------------------------------------|--------------------------------------------------------------------| 
| Canopy (code)                         | <https://github.com/canopy-datahub>                                |
| Canopy (production)                   | <https://canopy.stanford.edu/>                                     |
| Canopy tutorial — Submission Workflow | <https://canopy.stanford.edu/tutorial?tutorial=submissionWorkflow> |
| Canopy tutorial — Data Access Control | <https://canopy.stanford.edu/tutorial?tutorial=dataAccessControl>  |
| NIH RADx Data Hub (paper)             | <https://publichealth.jmir.org/2025/1/e72677/>                     |
| NIH RADx Data Hub (website)           | <https://radxdatahub.nih.gov/>                                     |
| CEDAR Workbench                       | <https://cedar.metadatacenter.org/>                                |
| Model Context Protocol                | <https://modelcontextprotocol.io/>                                 |
| Install guide                         | [INSTALL.md](INSTALL.md)                                           |
| CEDAR Artifact MCP (Java)             | <https://github.com/metadatacenter/cedar-artifact-mcp>             |
| BioPortal Term MCP (Python / `uv`)    | <https://github.com/metadatacenter/bioportal-term-mcp>             |
| CEDAR Artifact REST MCP (Java)        | <https://github.com/metadatacenter/cedar-artifact-rest-mcp>        |
| CEDAR CEE MCP (Java)                  | <https://github.com/metadatacenter/cedar-cee-mcp>                  |

## License

[GPL-3.0](LICENSE).

## CoFest 2026 Participant Forks

The repositories below are forks created by participants in the Canopy: AI-Assisted Metadata Generation project during CoFest 2026.

| Participant     | Institution                              | Email                                                                 | Project Fork                                                                        |
| --------------- | ---------------------------------------- | --------------------------------------------------------------------- | ----------------------------------------------------------------------------------- |
| Anne Ketter     | Computercraft                            | [aketter@computercraft-usa.com](mailto:aketter@computercraft-usa.com) | [View repository](https://github.com/annekeCC/canopy-metadata-ccncbi-2026)          |
| Anoushka Prabhu | Johns Hopkins University                 | [anoushkaprabhu3@gmail.com](mailto:anoushkaprabhu3@gmail.com)         | [View repository](https://github.com/anoushka-prabhu30/canopy-metadata-cofest-2026) |
| Aydan Gasimova  | California Medical Innovations Institute | [agasimova@calmi2.org](mailto:agasimova@calmi2.org)                   | Not yet available                                                                   |
| Daniel Kerchner | George Washington University             | [kerchner@gwu.edu](mailto:kerchner@gwu.edu)                           | [View repository](https://github.com/kerchner/canopy-metadata-cofest-2026)          |
| Harry Caufield  | Lawrence Berkeley National Laboratory    | [jhc@lbl.gov](mailto:jhc@lbl.gov)                                     | Not yet available                                                                   |
| Nahid Zeinali   | California Medical Innovations Institute | [nzeinali@calmi2.org](mailto:nzeinali@calmi2.org)                     | [View repository](https://github.com/Nahidzeinali-web/canopy-metadata-cofest-2026)  |
