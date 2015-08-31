#!/usr/bin/python

import json
import logging
import os
# import config
import matplotlib.pyplot as plt
import re
from numpy import *

################################################################################
# Configuration
################################################################################

# Set logging level to DEBUG
logger = logging.getLogger()
handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s %(levelname)-8s %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.DEBUG)

################################################################################
# Analysing logs
################################################################################


def load_json(path):
    result = []
    with open("%s/%s" % (".", path), 'r') as f:
        for line in f.readlines():
            try:
                data = json.loads(line)
                result += [data]
            except:
                pass
    return result


def load_rome_queries(path):
    result = load_json(path)
    return result


def load_napi_queries(path):
    result = load_json(path)
    return result


def generate_napi_graph(napi_queries, vms_count_over_time, method=None):
    filtered_napi_queries = filter(lambda x: x["method"] == method,
                                   napi_queries) if method else napi_queries
    # time_start = min(map(lambda x: x["timestamp"], napi_queries))
    time_start = 0
    napi_queries_x = map(lambda x: (x["timestamp"] - time_start) / 1000.0,
                         filtered_napi_queries)
    napi_queries_y = map(lambda x: x["duration"] / 1000.0, filtered_napi_queries)
    vms_count_over_time_x = map(lambda x: (x["timestamp"] - time_start) / 1000.0,
                                vms_count_over_time)
    vms_count_over_time_y = map(lambda x: x["count"], vms_count_over_time)

    fig, ax1 = plt.subplots()
    ax1.plot(napi_queries_x, napi_queries_y, 'ro')
    ax1.set_xlabel('time (s)')
    ax1.axis([min(napi_queries_x),max(napi_queries_x),0,max(napi_queries_y)])
    ax1.set_ylabel('duration (s)', color='r')
    ax2 = ax1.twinx()
    ax2.plot(vms_count_over_time_x, vms_count_over_time_y, 'b.')
    ax2.set_ylabel('VMs count', color='b')
    figure_name = method if method else "all_methods"
    plt.title(figure_name)
    plt.savefig("results/apis/%s" % (figure_name))


def extract_model_set(rome_query):
    json_repr = json.loads(rome_query["description"])
    models = json_repr["models"].replace("Selection(<class '", "").replace(
        "'>.*)", "").replace("[", "").replace("]", "").replace(
            "nova.db.discovery.models.", "").split(",")
    corrected_models = map(lambda x: str(re.sub(r"'.*", "", x).strip()), models)
    return sorted(set(corrected_models))


def get_rome_duration(rome_query):
    duration = (
        rome_query["building_query"] + rome_query["loading_objects"] +
        rome_query["filtering_tuples"] + rome_query["building_tuples"] +
        rome_query["reordering_columns"] + rome_query["selecting_attributes"])
    return duration


def get_rome_criterion_count(rome_query):
    json_repr = json.loads(rome_query["description"])
    criterions_count = len(json_repr["criterions"].split(","))
    return criterions_count


def generate_rome_graph(rome_queries, vms_count_over_time, models=None):
    filtered_rome_queries = filter(lambda x: extract_model_set(x) == models,
                                   rome_queries) if models else rome_queries
    if len(rome_queries) == 0:
        return
    # time_start = min(map(lambda x: x["timestamp"], rome_queries))
    time_start = 0
    rome_queries_x = map(lambda x: (x["timestamp"] - time_start) / 1000.0,
                         filtered_rome_queries)
    rome_queries_y = map(lambda x: get_rome_duration(x) / 1000.0,
                         filtered_rome_queries)
    vms_count_over_time_x = map(lambda x: (x["timestamp"] - time_start) / 1000.0,
                                vms_count_over_time)
    vms_count_over_time_y = map(lambda x: x["count"], vms_count_over_time)

    fig, ax1 = plt.subplots()
    ax1.plot(rome_queries_x, rome_queries_y, 'ro')
    ax1.set_xlabel('time (s)')
    ax1.axis([min(rome_queries_x),max(rome_queries_x),0,max(rome_queries_y)])
    ax1.set_ylabel('duration (s)', color='r')
    ax2 = ax1.twinx()
    ax2.plot(vms_count_over_time_x, vms_count_over_time_y, 'b.')
    ax2.set_ylabel('VMs count', color='b')
    figure_name = "_".join(models) if models else "all_models"
    plt.title(figure_name)
    plt.savefig("results/queries/%s" % (figure_name))


def main():

    import os

    experiment_data = {
        "experiments" : {},
        "metrics": {}
    }

    for kind in os.listdir('exps_data'):
        kind_folder_name = 'exps_data/%s' % (kind)
        if os.path.isdir(kind_folder_name):
            for dirname in [x for x in os.listdir(kind_folder_name) if os.path.isdir(kind_folder_name+"/"+x)]:
                dirname = "%s/%s" % (kind_folder_name, dirname)

                skip = True
                try:
                    os.path.isdir("%s/results")
                    skip = False
                except:
                    pass
                if skip:
                    continue

                """ Create / Clean "result" folder """
                os.system("rm -r results")
                os.system("mkdir -p results")
                os.system("mkdir -p results/apis")
                os.system("mkdir -p results/queries")
                os.system("mkdir -p results/cumulative")
                os.system("mkdir -p results/tables")

                """ Find metadata about the experiment """
                tab = dirname.split("/")
                experiment_class = tab[1]
                storage_solution = "redis" if "redis" in dirname else "sqlalchemy"
                tab = dirname.split("_")
                over_position = tab.index("over")
                storage_solution = tab[over_position+2]
                nb_nodes = int(tab[over_position+1])
                nb_controlers = int(tab[over_position-1])
                print("%s@%s with %i/%i" % (experiment_class, storage_solution, nb_controlers, nb_nodes))
                
                os.system("mkdir -p results/cumulative/%s/%s_%i_%i" % (experiment_class, storage_solution, nb_controlers, nb_nodes))

                """ Data structures for logs """
                rome_queries = []
                napi_queries = []
                vms_count_over_time = []
                napi_methods = []
                """ Consolidating results """
                for host in [x for x in os.listdir(dirname+"/data") if os.path.isdir(dirname+"/data/"+x)]:
                    host_shortname = host.split(".")[0]
                    folder = "%s/data/%s" % (dirname, host_shortname)
                    try:
                        rome_queries += load_rome_queries("%s/rome.log" % (folder))
                    except:
                        pass
                    try:
                        napi_queries += load_napi_queries("%s/db_api.log" % (folder))
                    except:
                        pass
                """ Sorting results according to timestamp field """
                rome_queries = sorted(rome_queries, key=lambda x: x["timestamp"])
                napi_queries = sorted(napi_queries, key=lambda x: x["timestamp"])
                # Computing VMs count over time
                instance_get_all_by_filters_occurences = filter(
                    lambda x: x["method"] == "instance_get_all_by_filters", napi_queries)
                vms_count_over_time = map(lambda x: {
                    "timestamp": x["timestamp"],
                    "count": len(x["result"].split("Lazy")) + len(
                        x["result"].split("hostname"))
                }, instance_get_all_by_filters_occurences)
                # Computing methods of napi
                napi_methods = list(set(map(lambda x: x["method"], napi_queries)))
                # Printing details
                logger.info("rome_queries: %i" % (len(rome_queries)))
                logger.info("napi_queries: %i" % (len(napi_queries)))
                # Create / Clean "result" folder
                os.system("rm -r results")
                os.system("mkdir -p results")
                os.system("mkdir -p results/apis")
                os.system("mkdir -p results/queries")
                # Ploting n-api data
                logger.info("Generating graph for all n-api methods")
                generate_napi_graph(napi_queries, vms_count_over_time)
                for method in napi_methods:
                    logger.info("Generating graph for %s" % (method))
                    generate_napi_graph(napi_queries, vms_count_over_time, method)
                # Ploting rome queries data
                logger.info("Generating graph for all rome queries")
                rome_models = map(lambda x: extract_model_set(x), rome_queries)
                unique_rome_models = [list(x) for x in set(tuple(x) for x in rome_models)]
                generate_rome_graph(rome_queries, vms_count_over_time)
                for model in unique_rome_models:
                    logger.info("Generating graph for %s" % (model))
                    generate_rome_graph(rome_queries, vms_count_over_time, model)
                # Analysing if there is a match between criterion size and duration
                criterion_duration_list = map(lambda x: {
                    "duration": get_rome_duration(x),
                    "criterions_count": get_rome_criterion_count(x)
                }, rome_queries)
                criterions_counts = set(map(lambda x: x["criterions_count"],
                                            criterion_duration_list))
                print("Duration statistics according to number of criterions")
                for criterions_count in criterions_counts:
                    durations = [item["duration"] for item in criterion_duration_list
                                 if item["criterions_count"] == criterions_count]
                    print("""%i -> {"avg": %i, "min": %i, "max": %i, "std": %i}""" %
                          (criterions_count, average(durations) / 1000.0, min(durations) /
                           1000.0, max(durations) / 1000.0, std(durations) / 1000.0))
                # Analysing if there is a match between model kind and duration
                print("Duration statistics according to type of model")
                models_duration_list = map(lambda x: {
                    "duration": get_rome_duration(x),
                    "models": str(extract_model_set(x)),
                    "query": x
                }, rome_queries)
                models_list = set(map(lambda x: x["models"], models_duration_list))
                models_statistics = []
                for models in models_list:
                    durations = [item["duration"] for item in models_duration_list
                                 if item["models"] == models]
                    models_statistics += [
                        {"models": models,
                         "durations": durations,
                         "count": len(durations)}
                    ]
                sorted_models_statistics = sorted(models_statistics,
                                                  key=lambda x: x["count"],
                                                  reverse=True)
                for statistic in sorted_models_statistics:
                    models = statistic["models"]
                    durations = statistic["durations"]
                    count = statistic["count"]
                    print("""%s -> {"avg": %i, "min": %i, "max": %i, "std": %i, "count": %i}"""
                          % (models, average(durations) / 1000.0, min(durations) / 1000.0,
                             max(durations) / 1000.0, std(durations) / 1000.0, count))
                # Analysing if there is a match between napi method kind and duration
                print("Statistics about API calls")
                napi_duration_list = map(
                    lambda x: {"duration": x["duration"],
                               "method": x["method"]}, napi_queries)
                napi_method_list = set(map(lambda x: x["method"], napi_duration_list))
                napi_statistics = []
                for napi_method in napi_method_list:
                    durations = [item["duration"] for item in napi_duration_list
                                 if item["method"] == napi_method]
                    # draw durations that are higher than 5 seconds
                    long_durations = [item["duration"] for item in napi_duration_list
                                 if item["method"] == napi_method and item["duration"] > 5000]
                    print(long_durations)
                    napi_statistics += [{
                        "method": napi_method,
                        "durations": durations,
                        "count": len(durations)
                    }]
                sorted_napi_statistics = sorted(napi_statistics,
                                                key=lambda x: x["count"],
                                                reverse=True)
                for statistic in sorted_napi_statistics:
                    method = statistic["method"]
                    durations = statistic["durations"]
                    count = statistic["count"]
                    print("""%s -> {"avg": %i, "min": %i, "max": %i, "std": %i, "count": %i}"""
                          % (method, average(durations) / 1000.0, min(durations) / 1000.0,
                             max(durations) / 1000.0, std(durations) / 1000.0, count))
                # Print details of long queries:
                print(sorted(models_duration_list, key=lambda x: x["duration"], reverse=True)[0:20])
                # Put results folder in the exp directory
                os.system("cp -r results %s" % (dirname))

if __name__ == '__main__':
    main()
