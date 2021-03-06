
import sys, os
if '..' not in sys.path:
    sys.path.append('..')

import numpy as np
import random as rd
import pandas as pd
import pickle
import multiprocessing
import argparse
from lib.measures import *
from lib.experiment import Experiment, options_to_str, process_command_line
from lib.calibrationSettings import calibration_lockdown_dates, calibration_mob_paths, calibration_states
from lib.calibrationFunctions import get_calibrated_params

TO_HOURS = 24.0

if __name__ == '__main__':

    name = 'tracing'
    start_date = '2021-01-01'
    end_date = '2021-05-01'
    random_repeats = 48
    full_scale = True
    verbose = True
    seed_summary_path = None
    set_initial_seeds_to = {}
    expected_daily_base_expo_per100k = 5 / 7

    # contact tracing experiment parameters
    settings = [
        (['isolate', 'test'], 48.0, 100000, 'basic'),
        (['isolate', 'test'], 48.0, 30, 'advanced'),
        (['isolate'], 48.0, None, None),
        (['isolate'], 3.0, None, None),
    ]

    # seed
    c = 0
    np.random.seed(c)
    rd.seed(c)

    # command line parsing
    args = process_command_line()
    country = args.country
    area = args.area
    cpu_count = args.cpu_count

    # Load calibrated parameters up to `maxBOiters` iterations of BO
    maxBOiters = 40 if area in ['BE', 'JU', 'RH'] else None
    calibrated_params = get_calibrated_params(country=country, area=area,
                                              multi_beta_calibration=False,
                                              maxiters=maxBOiters)

    # create experiment object
    experiment_info = f'{name}-{country}-{area}'
    experiment = Experiment(
        experiment_info=experiment_info,
        start_date=start_date,
        end_date=end_date,
        random_repeats=random_repeats,
        cpu_count=cpu_count,
        full_scale=full_scale,
        verbose=verbose,
    )

    # contact tracing experiment for various options
    for (smart_tracing_actions,
         test_delay,
         contacts_tested,
         test_policy) in settings:

        # measures
        max_days = (pd.to_datetime(end_date) - pd.to_datetime(start_date)).days
        
        m = [
            SocialDistancingForSmartTracing(
                t_window=Interval(0.0, TO_HOURS * max_days), 
                p_stay_home=1.0, 
                smart_tracing_isolation_duration=TO_HOURS * 14.0),
            SocialDistancingForSmartTracingHousehold(
                t_window=Interval(0.0, TO_HOURS * max_days),
                p_isolate=1.0,
                smart_tracing_isolation_duration=TO_HOURS * 14.0),
            SocialDistancingSymptomaticAfterSmartTracing(
                t_window=Interval(0.0, TO_HOURS * max_days),
                p_stay_home=1.0,
                smart_tracing_isolation_duration=TO_HOURS * 14.0),
            SocialDistancingSymptomaticAfterSmartTracingHousehold(
                t_window=Interval(0.0, TO_HOURS * max_days),
                p_isolate=1.0,
                smart_tracing_isolation_duration=TO_HOURS * 14.0),
            ]

        # set testing params via update function of standard testing parameters
        def test_update(d):
            d['smart_tracing_actions'] = smart_tracing_actions
            d['test_reporting_lag'] = test_delay
            d['tests_per_batch'] = 100000

            # isolation
            d['smart_tracing_policy_isolate'] = 'basic'
            d['smart_tracing_isolated_contacts'] = 100000
            d['smart_tracing_isolation_duration'] = 14 * TO_HOURS,

            # testing
            d['smart_tracing_policy_test'] = test_policy
            d['smart_tracing_tested_contacts'] = contacts_tested

            return d


        simulation_info = options_to_str(
            tracing='+'.join(smart_tracing_actions),
            delay=test_delay,
            contacts_tested=contacts_tested,
            test_policy=test_policy,
        )
            
        experiment.add(
            simulation_info=simulation_info,
            country=country,
            area=area,
            measure_list=m,
            test_update=test_update,
            seed_summary_path=seed_summary_path,
            set_initial_seeds_to=set_initial_seeds_to,
            set_calibrated_params_to=calibrated_params,
            full_scale=full_scale,
            expected_daily_base_expo_per100k=expected_daily_base_expo_per100k)
                
    print(f'{experiment_info} configuration done.')

    # execute all simulations
    experiment.run_all()

