import os
import dash
import dash_bootstrap_components as dbc
from dash import dash_table, Input, Output, State, html, dcc
import pandas as pd
import requests
import json
import base64
import io
from jproperties import Properties
from markdownify import markdownify as md


# instantiate config
configs = Properties()
# load properties into configs
with open('app-config.properties', 'rb') as config_file:
    configs.load(config_file)
# read into dictionary
configs_dict = {}
items_view = configs.items()
for item in items_view:
    configs_dict[item[0]] = item[1].data

# For LLM call
SERVER_URL = "Update Your server URL"
API_KEY = os.getenv("WATSONX_API_KEY", default="Update API Key Here")
HEADERS = {
        'accept': 'application/json',
        'content-type': 'application/json',
        'Authorization': 'Bearer {}'.format(API_KEY)
    }

# ---- UI code ----

app = dash.Dash(external_stylesheets=[dbc.themes.BOOTSTRAP, 'https://fonts.googleapis.com/css?family=IBM+Plex+Sans:400,600&display=swap'])
app.title = configs_dict['tabtitle']

navbar_main = dbc.Navbar([
            dbc.Row([
                    dbc.Col(configs_dict['navbartitle'],
                        style={'fontSize': '0.875rem','fontWeight': '600'},
                    ),
                ]
            )
        ],
    style={'paddingLeft': '1rem', 'height': '3rem', 'paddingRight': '2rem', 'borderBottom': '1px solid #393939', 'color': '#fff'},
    class_name = "bg-dark"
)

user_input = dbc.InputGroup([
        dbc.Textarea(id="user-input", 
                     value=configs_dict['sample_text'],
                     placeholder=configs_dict['input_placeholder_text'],
                     rows=configs_dict['input_h_rows'] if configs_dict['layout'] == 'horizontal' else configs_dict['input_v_rows'],
                     style={'borderRadius': '0', 'borderTop': 'none', 'borderLeft': 'none', 'borderRight': 'none', 'backgroundColor': '#f4f4f4','borderBottomColor': '#8d8d8d', 'resize': 'none'}
                     ),
    ],
    className="mb-3",
)

generate_button = dbc.Button(
    configs_dict['generate_btn_text'], id="generate-button", outline=True, color="primary", n_clicks=0, className="carbon-btn"
)

buttonsPanel = dbc.Row([
                dbc.Col(generate_button),
            ]) if configs_dict['show_upload'] in ["true", "True"] else dbc.Row([
                    dbc.Col(generate_button, className="text-center"),
                ])

footer = html.Footer(
    dbc.Row([
        dbc.Col(configs_dict['footer_text'],className="p-3")]),
    style={'paddingLeft': '1rem', 'paddingRight': '5rem', 'color': '#c6c6c6', 'lineHeight': '22px'},
    className="bg-dark position-fixed bottom-0"
)

vertical_layout = dbc.Row(
                    [
                        dbc.Col(className="col-2"),
                        dbc.Col(
                            children=[
                                html.H5(configs_dict['Input_title']),
                                html.Div(user_input),
                                buttonsPanel,
                                html.Br(),
                                html.Hr(),
                                html.Div([
                                        # html.H5(configs.get('Output_title')),
                                        html.Div(id='generate-output')
                                    ],
                                    style={'padding': '1rem 1rem'}
                                ),
                            ],
                            className="col-8"
                        ),
                        dbc.Col(className="col-2"),
                    ],
                    className="px-3 pb-5"
                )

horizontal_layout = dbc.Row(
                    [
                        dbc.Col(className="col-1"),
                        dbc.Col(
                            children=[
                                html.H5(configs_dict['Input_title']),
                                html.Div(user_input),
                                buttonsPanel,
                                html.Br(),
                                html.Br(),
                            ],
                            className="col-5 border-end",
                            style={'padding': '1rem'}
                        ),
                        dbc.Col(
                            children=[
                                html.Div([
                                        # html.H5(configs.get('Output_title')),
                                        html.Div(id='generate-output')
                                    ],
                                    style={'padding': '1rem 3rem'}
                                ),
                            ],
                            className="col-5"
                        ),
                        dbc.Col(className="col-1"),
                    ],
                    className="px-3 pb-5"
                )

app.layout = html.Div(children=[
                    navbar_main,
                    html.Br(),
                    html.Br(),
                    horizontal_layout if configs_dict['layout'] == 'horizontal' else vertical_layout,
                    html.Br(),
                    html.Br(),
                    footer
], className="bg-white", style={"fontFamily": "'IBM Plex Sans', sans-serif"}
)

# ---- end UI code ----

def parse_output(res, type):
    parseoutput = []
    if(type == 'text'):
        return res
    if(type == 'label'):
        return dbc.Badge(res, color="#1192e8", style={'borderRadius': '12px','marginLeft':'8px','paddingLeft':'16px', 'paddingRight':'16px'})
    elif(type == 'key-value'):
        pairs = res.split(',')
        for pair in pairs:
            k, v = pair.split(':')
            parseoutput.append(html.Div([html.B(k+':'), v], className="key-value-div"))
        return html.Div(parseoutput, className="key-value-div-parent")
    elif(type == 'markdown'):
        return html.Div([dcc.Markdown(md(res)), html.A("Redirect to IBM Security QRadar Suite", href='https://deployment-a9locxun.xdr.security.ibm.com/app/data-explorer?searchTab=recentSearches', target="_blank")])

# Codegen API call
def codegen_fn(text, codegen_payload_json, type):
    REQ_URL = SERVER_URL+'/v1/generate'
    codegen_payload_json['inputs'] = [text]
    print("calling LLM-Codegen", print("calling LLM-Codegen"))
    response_llm = requests.post(REQ_URL, headers=HEADERS, data=json.dumps(codegen_payload_json))
    response_llm_json = response_llm.json()
    print(response_llm_json['results'][0]['generated_text'])
    print(type)
    answer = "<html><pre width= '100%'>" + response_llm_json['results'][0]['generated_text'] + "</pre></html>"
    return parse_output(answer, type)

# LLM Call
@app.callback(
    Output('generate-output', 'children'),
    Input('generate-button', 'n_clicks'),
    State('user-input', 'value'),
    prevent_initial_call=True
)
def generate_output_llm(n, text):
    output = []
    actions = configs_dict['generate_btn_actions'].split(',')
    labels = configs_dict['generate_btn_output_labels'].split(',')
    payloads = configs_dict['generate_btn_payload_files'].split(',')
    types = configs_dict['generate_btn_output_type'].split(',')
    
    for action, label, payload_file, type in zip(actions, labels, payloads, types):
        try:
          with open('payload/{}.json'.format(payload_file)) as payload_f:
            payload_f_json = json.load(payload_f)

          if(action == "codegen"):
            output.append(html.Div([html.H5(label), codegen_fn(text, payload_f_json, type)], className="output-div", style={"backgroud-color": "green"}))
        except Exception as e:
          print(action, e)
    return output

# For loading spinner
@app.callback(
    Output('generate-output', 'children', allow_duplicate=True),
    Input('generate-button', 'n_clicks'),
    State('user-input', 'value'),
    prevent_initial_call=True
)
def generate_output_llm(n, text):
    return [dbc.Spinner(color="primary", size="sm"), " Please wait..."]

# main -- runs on localhost. change the port to run multiple apps on your machine
if __name__ == '__main__':
    SERVICE_PORT = os.getenv("SERVICE_PORT", default="8057")
    app.run(host="0.0.0.0", port=SERVICE_PORT, debug=False, dev_tools_hot_reload=False)
