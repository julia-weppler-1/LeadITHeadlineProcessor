import streamlit as st

def about_tab():
    text = """
## About the GPT-Batch Headline Processor (beta)



## Terms of Use

### Open Access to the Data Sets
The GPT-Batch Headline Processor (beta) tool is made available for public use with the intention of promoting transparency and fostering knowledge sharing in environmental project developments.

**Date of release**: .

### Tool Attribution
The tool was created by the following contributors: Miquel Muñoz Cabré, Julia Weppler, Eileen Torres Morales, William Babis


### Licensing and Copyright Information
The Stockholm Environment Institute (SEI) holds the copyright for the GPT-Batch Headline Processor (beta) tool. It is licensed under the [Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International License (CC BY-NC-SA)](https://creativecommons.org/licenses/by-nc-sa/4.0/).

### Usage Guidelines
By using the tool, you agree to the following terms:
- **Non-commercial use**: The tool is provided for non-commercial, academic, and research purposes only. Any commercial use or redistribution requires permission from the Stockholm Environment Institute.
- **Attribution**: You must provide appropriate credit to the authors and the Stockholm Environment Institute, as specified in the citation section.
- **ShareAlike**: Any derivative works created from this tool must be licensed under the same Creative Commons License (CC BY-NC-SA).

If you have any questions or need further information, feel free to reach out via email at [aipolicyreader@sei.org](mailto:aipolicyreader@sei.org) or consult the documentation provided with the tool.

## Acknowledgments
We would like to thank the Stockholm Environment Institute (SEI) for their support in the development of this tool. Their mission to promote environmental sustainability through evidence-based research has been a key inspiration for this project.
"""
    st.markdown(text)
