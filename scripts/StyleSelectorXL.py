#modified StyleSelector for loading your own JSON

import contextlib

import gradio as gr
from modules import scripts, shared, script_callbacks
from modules.ui_components import FormRow, FormColumn, FormGroup, ToolButton
import json
import os
import random

json_path = ""
styleNames = ""
folder = scripts.basedir()
json_list = [f for f in os.listdir(folder) if f.endswith('.json')]

def get_json_content(json_path_in):
    try:
        with open(json_path_in, 'rt', encoding="utf-8") as file:
            json_data = json.load(file)
            return json_data
    except Exception as e:
        print(f"A Problem occurred: {str(e)}")

def read_sdxl_styles(json_data_in):
    # Check that data is a list
    if not isinstance(json_data_in, list):
        print("Error: input data must be a list")
        return None

    names = []

    # Iterate over each item in the data list
    for item in json_data_in:
        # Check that the item is a dictionary
        if isinstance(item, dict):
            # Check that 'name' is a key in the dictionary
            if 'name' in item:
                # Append the value of 'name' to the names list
                names.append(item['name'])
    names.sort()
    return names

def createPositive(style_name, positive):
    json_data = get_json_content(json_path)
    try:
        # Check if json_data is a list
        if not isinstance(json_data, list):
            raise ValueError(
                "Invalid JSON data. Expected a list of templates.")

        for template in json_data:
            # Check if template contains 'name' and 'prompt' fields
            if 'name' not in template or 'prompt' not in template:
                raise ValueError(
                    "Invalid template. Missing 'name' or 'prompt' field.")

            # Replace {prompt} in the matching template
            if template['name'] == style_name:
                positive = template['prompt'].replace(
                    '{prompt}', positive)

                return positive

        # If function hasn't returned yet, no matching template was found
        raise ValueError(f"No template found with name '{style_name}'.")

    except Exception as e:
        print(f"An error occurred: {str(e)}")

def createNegative(style_name, negative):
    json_data = get_json_content(json_path)
    try:
        # Check if json_data is a list
        if not isinstance(json_data, list):
            raise ValueError(
                "Invalid JSON data. Expected a list of templates.")

        for template in json_data:
            # Check if template contains 'name' and 'prompt' fields
            if 'name' not in template or 'prompt' not in template:
                raise ValueError(
                    "Invalid template. Missing 'name' or 'prompt' field.")

            # Replace {prompt} in the matching template
            if template['name'] == style_name:
                json_negative_prompt = template.get('negative_prompt', "")
                if negative:
                    negative = f"{json_negative_prompt}, {negative}" if json_negative_prompt else negative
                else:
                    negative = json_negative_prompt

                return negative

        # If function hasn't returned yet, no matching template was found
        raise ValueError(f"No template found with name '{style_name}'.")

    except Exception as e:
        print(f"An error occurred: {str(e)}")

class StyleSelectorXL(scripts.Script):
    def __init__(self) -> None:
        super().__init__()

    def title(self):
        return "Style Selector for SDXL 1.0"

    def show(self, is_img2img):
        return scripts.AlwaysVisible

    def ui(self, is_img2img):
        enabled = getattr(shared.opts, "enable_styleselector_by_default", True)
        with gr.Group():
            with gr.Accordion("SDXL Styles NEW", open=enabled):
                with FormRow():
                    with FormColumn(min_width=160):
                        is_enabled = gr.Checkbox(
                            value=enabled, label="Enable Style Selector", info="Enable Or Disable Style Selector ")
                    with FormColumn(elem_id="Randomize Style"):
                        randomize = gr.Checkbox(
                            value=False, label="Randomize Style", info="This Will Override Selected Style")

                def getStyles(json_value):
                    global json_path
                    global styleNames
                    json_path = os.path.join(folder, json_value)
                    json_data_out = get_json_content(json_path)
                    styleNames = read_sdxl_styles(json_data_out)
                    return styleNames

                styleNames = getStyles(json_list[0]) if json_list else []

                with FormRow():
                    with FormColumn(min_width=160):
                        json_file = gr.Dropdown(
                            label="Select Stylefile",
                            choices=json_list,
                            value=json_list[0] if json_list else "Please put styles in folder",
                            multiselect=False
                        )
                        style_ui_type = shared.opts.data.get(
                            "styles_ui",  "radio-buttons")
                        
                        if style_ui_type == "select-list":
                           style = gr.Dropdown(
                                label='Select Style', choices=styleNames, value=json_list[0], multiselect=False)
                        else:
                            style = gr.Radio(
                                label='Style', choices=styleNames, value=json_list[0], multiselect=False)

                        allstyles = gr.Checkbox(
                            value=False,
                            label="Generate All Styles In Order",
                            info=f"To Generate Your Prompt in All Available Styles, it's better to set batch count to {len(styleNames)} (Style Count)"
                        )

                        #Event Changer and Listener
                        def json_changer(selected_value):
                            styleNames_new = getStyles(selected_value)
                            return [style.update(choices=styleNames_new), allstyles.update(info=f"To Generate Your Prompt in All Available Styles, it's better to set batch count to {len(styleNames_new)} (Style Count)")]

                        json_file.change(json_changer, inputs=json_file, outputs=[style,allstyles])
                   
        return [is_enabled, randomize, allstyles, style]

    def process(self, p, is_enabled, randomize, allstyles, style):
        if not is_enabled:
            return

        if randomize:
            style = random.choice(styleNames)
        batchCount = len(p.all_prompts)

        if(batchCount == 1):
            # for each image in batch
            for i, prompt in enumerate(p.all_prompts):
                positivePrompt = createPositive(style, prompt)
                p.all_prompts[i] = positivePrompt
            for i, prompt in enumerate(p.all_negative_prompts):
                negativePrompt = createNegative(style, prompt)
                p.all_negative_prompts[i] = negativePrompt
        if(batchCount > 1):
            styles = {}
            for i, prompt in enumerate(p.all_prompts):
                if(randomize):
                    styles[i] = random.choice(styleNames)
                else:
                    styles[i] = style
                if(allstyles):
                    styles[i] = styleNames[i % len(styleNames)]
            # for each image in batch
            for i, prompt in enumerate(p.all_prompts):
                positivePrompt = createPositive(
                    styles[i] if allstyles else styles[0], prompt)
                p.all_prompts[i] = positivePrompt
            for i, prompt in enumerate(p.all_negative_prompts):
                negativePrompt = createNegative(
                    styles[i] if allstyles else styles[0], prompt)
                p.all_negative_prompts[i] = negativePrompt

        p.extra_generation_params["Style Selector Enabled"] = True
        p.extra_generation_params["Style Selector Randomize"] = randomize
        p.extra_generation_params["Style Selector Style"] = style

    def after_component(self, component, **kwargs):
        # https://github.com/AUTOMATIC1111/stable-diffusion-webui/pull/7456#issuecomment-1414465888 helpfull link
        # Find the text2img textbox component
        if kwargs.get("elem_id") == "txt2img_prompt":  # postive prompt textbox
            self.boxx = component
        # Find the img2img textbox component
        if kwargs.get("elem_id") == "img2img_prompt":  # postive prompt textbox
            self.boxxIMG = component

        # this code below  works aswell, you can send negative prompt text box,provided you change the code a little
        # switch  self.boxx with  self.neg_prompt_boxTXT  and self.boxxIMG with self.neg_prompt_boxIMG

        # if kwargs.get("elem_id") == "txt2img_neg_prompt":
            #self.neg_prompt_boxTXT = component
        # if kwargs.get("elem_id") == "img2img_neg_prompt":
            #self.neg_prompt_boxIMG = component

def on_ui_settings():
    section = ("styleselector", "Style Selector")
    shared.opts.add_option("styles_ui", shared.OptionInfo(
        "radio-buttons", "How should Style Names Rendered on UI", gr.Radio, {"choices": ["radio-buttons", "select-list"]}, section=section))

    shared.opts.add_option(
        "enable_styleselector_by_default",
        shared.OptionInfo(
            True,
            "enable Style Selector by default",
            gr.Checkbox,
            section=section
            )
    )
script_callbacks.on_ui_settings(on_ui_settings)
