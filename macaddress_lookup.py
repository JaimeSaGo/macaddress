#!/usr/bin/env python3

# =+=+=+=+=+= Import Libraries =+=+=+=+=+=
import argparse
import logging
import os
import re
import sys
import urllib.request
import json


# =+=+=+=+=+= Define Functions =+=+=+=+=+=

def validate_macaddress(macaddress_input):
    return re.match("^([0-9A-Fa-f]{2}[:.-]?){5}([0-9A-Fa-f]{2})$", macaddress_input.strip())

def request_builder(macaddress_input, apikey):
    api_macaddress_url = "https://api.macaddress.io/v1"
    parameters = {"output": "json", "search": macaddress_input}
    url_encode = "{0}?{1}".format(api_macaddress_url, urllib.parse.urlencode(parameters))
    header = {"X-Authentication-Token": apikey}
    request_url = urllib.request.Request(url_encode, headers=header)
    return request_url

def request_sender(request):
    try:
        response = urllib.request.urlopen(request)
        output = response.read().decode("utf-8")
        return output
    except urllib.error.HTTPError:
        logging.error(
            "status code:{0} message:{1}".format(response.status, response.msg)
        )
        exit(response.status)
    finally:
        response.close()

def recursive_key_lookup(inp_dict):
    for key, value in inp_dict.items():
        if type(value) is dict:
            yield (key)
            yield from recursive_key_lookup(value)
        else:
            yield (key)

def match_key(inp_dict, query_val):
    key_list = []
    for key in recursive_key_lookup(inp_dict):
        key_list.append(key)
    for key in key_list:
        if query_val.lower() in key.lower():
            return key
    return None

def recursive_val_lookup(key, inp_dict):
    if key in inp_dict:
        return inp_dict[key]
    for val in inp_dict.values():
        if isinstance(val, dict):
            nested_val = recursive_val_lookup(key, val)
            if nested_val is not None:
                return nested_val
    return None

def formatted_output(response, query_list, output_type):
    output_str = ""
    output_dict = {}
    try:
        response_dict = json.loads(response)
        for query in query_list:
            search_key = match_key(response_dict, query)
            if search_key is not None:
                search_val = recursive_val_lookup(search_key, response_dict)
                output_dict[query] = search_val
            else:
                output_dict[query] = None
    except ValueError as e:
        logging.error("Could not load JSON output to string.")
    if output_type == "json":
        output_str = json.dumps(output_dict)
    elif output_type == "csv":
        output_str = (
            ",".join(output_dict.keys())
            + "\n"
            + ",".join('"{0}"'.format(val) for val in output_dict.values())
        )
    else:
        if len(output_dict) == 1:
            output_str = next(iter(output_dict.values()))
        else:
            output_str = "\n".join(
                "{!s}={!s}".format(key, val) for (key, val) in output_dict.items()
            )
    return output_str

def main():
    # =+=+=+=+=+= Define Structure =+=+=+=+=+=
    structure = argparse.ArgumentParser(description="This Query is to get the macaddress info associated by macaddress.io.")
    structure.add_argument("macaddress_id", type=str, help=" = macaddress of the device")
    structure.add_argument("-o", "--output", help="output format control, accepted values are json, csv, minimal", dest="output", default="minimal")
    structure.add_argument("-q", "--query", help="query fields, one or multiple comma seperated eg. name,transmission,valid,blockfound", dest="query", default="name")
    structure.add_argument("-r", "--rawjson", help="return raw json from the server that can be piped to jq for other fields", action="store_true")
    structure.add_argument("-v", "--verbose", help="make output more verbose sets to DEBUG", action="store_true")

    args = structure.parse_args()
    macaddress_input = args.macaddress_id
    query_fields = args.query
    output_type = args.output

    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)
    try:
        apikey = os.environ["KEY_API_MA"]
        if apikey == "":
            logging.error("Please set the environment variable KEY_API_MA")
            sys.exit(1)
    except KeyError:
        logging.error("Please set the environment variable KEY_API_MA")
        sys.exit(1)
    if not validate_macaddress(macaddress_input):
        logging.error("Could not validate macaddress_input")
        sys.exit(1)
    response = request_sender(request_builder(macaddress_input, apikey))
    if args.rawjson:
        print(response)
        sys.exit(0)
    query_list = [x.strip() for x in query_fields.split(",")]
    print(formatted_output(response, query_list, output_type))

if __name__ == "__main__":
    main()
