import json
from data_handling.Nomad_API import *
import yaml
import zipfile
import time


def _getPoweredAxes(arr):
    axes = []
    for i in range(len(arr)):
        if arr[i]:
            axes.append(str(i+1))
    return axes


def _getYamlMagnetrons(dic, power_axes):
    axes = _getPoweredAxes(power_axes)
    return [_getYamlMagnetron(dic, axis) for axis in axes]


def _getYamlMagnetron(dic, axis):
    magnetron = {
        'name' : dic['source_' + axis + '_material'],
        'material' : {
            'name' : dic['source_' + axis + '_material'],
            'lab_id' : dic['source_' + axis + '_target_id'],
        },
        'vapor_source' : {
            'setpoints' : {
            'set_power' : dic['source_' + axis + '_set_power_[W]'],
            'set_voltage' : None,
            'set_current' : None
            },
            'power' : {
                'values' : dic['source_' + axis + '_act_power_[W]'],
                'times' : dic['time_[s]'],
                'mean' : dic['source_' + axis + '_act_power_[W]_mean'],
                'error' : dic['source_' + axis + '_act_power_[W]_mean']
            },
            'voltage' : {
                'values' : dic['source_' + axis + '_voltage_[V]'],
                'times' : dic['time_[s]'],
                'mean' : dic['source_' + axis + '_voltage_[V]_mean'],
                'error' : dic['source_' + axis + '_voltage_[V]_std'],
            },
            'current' : {
                'values' : [],
                'times' : dic['time_[s]'],
                'mean' : None,
                'error' : None
            },
            'power_supply' : {
                'instrument_id' : dic['source_' + axis + '_supply'],
                'supply_type' : dic['source_' + axis + '_mode'],
                'ramp_rate' : dic['source_' + axis + '_ramp_rate_[W/s]']
            }
        },
        'vapor_distribution' : {
                'shape' : "Knudsen model: dm/dt = A(n+1)cos(theta)cos^n(phi) / 2(pi)r^2",
                'n_parameter' : dic['n'],
                'A_parameter' : dic['A'],
                'origin' : {
                    'center_xyz' : dic['source_' + axis + '_position'],
                    'center_normal' : dic['source_' + axis + '_direction'],
                    'rotation' : None
                }
        }
    }
    return magnetron


def _getYamlQCM(dictionary, i):
    prefix = 'qcm_' + str(i) + '_'
    yamlQCM = {
            'crystal_info' : {
                'info' : None,
                'resonant_frequency' : None
            },
            'sensor_data' : {
                'values' : dictionary[prefix + 'frequency_[Hz]'],
                'mean' : dictionary[prefix + 'frequency_[Hz]_mean'],
                'error' : None,
                'slope' : dictionary[prefix + 'frequency_rate_[/s2]'],
                'slope_error': dictionary[prefix + 'frequency_rate_[/s2]_error']
            },
            'remaining_lifetime' : {
                'value' : dictionary[prefix + 'lifetime_[%]']
            },
            'mass_deposition_rate' : {
                'value' : dictionary[prefix + 'mass_rate_[ng/cm2s]'],
                'error' : dictionary[prefix + 'mass_rate_[ng/cm2s]_error']
            },
            'position' : {
                'center_xyz' : dictionary[prefix + 'position'],
                'center_normal' : dictionary[prefix + 'direction'],
                'rotation' : None
            }            
        }
    return yamlQCM


def _getYamlEnv(dictionary):
    environment = {
        'gas_flow' : {
            'values' :  dictionary['flow_[sccm]'],
            'mean' : dictionary['flow_[sccm]_mean'],
            'error' : dictionary['flow_[sccm]_std'],
            'gas' : 'Here we do the pubchem thing'
        },
        'setpoints' : {
            'pressure' : dictionary['set_pressure_[mTorr]'],
            'flow' : None,
        },
        'pressure' : {
            'values' : dictionary['act_pressure_[mTorr]'],
            'mean' : dictionary['act_pressure_[mTorr]_mean'],
            'error' : dictionary['act_pressure_[mTorr]_std']
        },
        'sensors' : [_getYamlQCM(dictionary, i+1) for i in range(3)] if dictionary['qcms_active'] else []
    }
    return environment
    


def data_to_zip(dic : dict, activated_axes : list):
    '''
    Turns the experiment dictionary that we have into a yaml file, dumps it, then zips it.
    
    data: the experiment dictionary
    activated axes: array of booleans indicating which magnetron axes are activated during the experiment
    '''
    
    data = {'data' : {
            'm_def' : "../uploads/bI_XzzqvSVm9lpOJMYQqgw/raw/automate-solar_schema.archive.yaml#/definitions/section_definitions/AutomateSolarSputterDeposition",  #if schema is updated, replace schema id(after uploads/)
            'quantity' : None,
            'name' : dic['run_id'],
            'lab_id' : "Uppsala University Åutomate-Solar",
            'datetime' : dic['series_start_datetime'],
            'location' : "Uppsala, Sweden",
            'method' : 'Magnetron Sputtering',
            'description' : f'{dic["campaign_description"]}, {dic["campaign_id"]}, {dic["series_description"]}',
            'steps' : [
                {
                    'name' : f'{dic["run_id"]}, Step 1', # Change this to dynamic when we have more steps
                    'duration' : dic['dwell_time_[s]'],
                    'start_time' : dic['series_start_datetime'],
                    'creates_new_thin_film' : dic['samples_produced'],
                    'sources' : _getYamlMagnetrons(dic, activated_axes),
                    'environment' : _getYamlEnv(dic)
                }
            ]
        }
    }
    
    with open('C:/Users/BERTHA/Documents/BEA-Supervisor/NOMAD/TEMP/data.archive.yaml', 'w') as outfile:
        yaml.dump(data, outfile, default_flow_style=False)
        
    with zipfile.ZipFile('C:/Users/BERTHA/Documents/BEA-Supervisor/NOMAD/TEMP/data.zip', 'w') as zipped_f:
        zipped_f.writestr("C:/Users/BERTHA/Documents/BEA-Supervisor/NOMAD/TEMP/data.archive.yaml", yaml.dump(data, default_flow_style=False))


def upload_zip():
    '''
    Upload the zipped file to NOMAD Oasis via API 
    '''
    
    file = 'C:/Users/BERTHA/Documents/BEA-Supervisor/NOMAD/secret.txt'
    password = ""
    with open(file, "r") as text:
        for line in text:
            password = line 
            
    username = 'jonathan.scragg@angstrom.uu.se'
    nomad_url = 'http://130.238.147.138/nomad-oasis/api/v1/' 
    
    token = get_authentication_token(nomad_url, username, password)
    upload_id = upload_to_NOMAD(nomad_url, token, 'C:/Users/BERTHA/Documents/BEA-Supervisor/NOMAD/TEMP/data.zip')
    
    # Give max 10 seconds for Nomad API to publish
    t_end = time.time() + 10
    while time.time() < t_end:
        if publish_upload(nomad_url, token, upload_id).ok:
            print("Data entry published to NOMAD")
            break
    
     
    


