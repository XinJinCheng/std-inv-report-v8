#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""cleanser_runner.py"""

__author__ = 'Gary.Z'

import os
import threading
import time
import shutil
from tempfile import NamedTemporaryFile

from data_cleansing.data_cleanser import *
from data_cleansing.rule.rules_assembler import *
from data_cleansing.filter.filter_chain import *
from data_cleansing.filter.cleanse_filter import *
from data_cleansing.salary_cleanser import *

logger = get_logger(__name__)


class DataCleanserRunner(threading.Thread):
    def __init__(self, input_file, output_file):
        threading.Thread.__init__(self)
        self._input_file = input_file
        self._output_file = output_file
        self._degree_filter = None
        self._with_rule_2_2 = False
        self._with_rule_7 = False
        self._sheet_tag = None
        self._trace_mode = False

    @property
    def with_rule_2_2(self):
        return self._with_rule_2_2

    @with_rule_2_2.setter
    def with_rule_2_2(self, with_rule_2_2):
        self._with_rule_2_2 = with_rule_2_2

    @property
    def with_rule_7(self):
        return self._with_rule_7

    @with_rule_7.setter
    def with_rule_7(self, with_rule_7):
        self._with_rule_7 = with_rule_7

    @property
    def trace_mode(self):
        return self._trace_mode

    @trace_mode.setter
    def trace_mode(self, trace_mode):
        self._trace_mode = trace_mode

    @property
    def degree_filter(self):
        return self._degree_filter

    @degree_filter.setter
    def degree_filter(self, degree_filter):
        self._degree_filter = degree_filter

    @property
    def sheet_tag(self):
        return self._sheet_tag

    @sheet_tag.setter
    def sheet_tag(self, sheet_tag):
        self._sheet_tag = sheet_tag

    def run(self):
        raise Exception('not implement')

    def _log_header(self):
        logger.info('')
        logger.info('############################## Cleansing start ##################################')
        logger.info('input file: \'{}\''.format(self._input_file))
        logger.info('output file: \'{}\''.format(self._output_file))
        if self._degree_filter is not None:
            logger.info('with degree filter: {}'.format(self.degree_filter))
        logger.info('with rule 2.2: {}'.format(self._with_rule_2_2))
        logger.info('with rule 7: {}'.format(self._with_rule_7))
        logger.info('trace mode: {}'.format(self._trace_mode))
        logger.info('#################################################################################')
        logger.info('')

    def _log_tailer(self):
        logger.info('')
        logger.info('############################## Cleansing end ##################################')
        logger.info('')


class DataCleanserMemoryRunner(DataCleanserRunner):
    def __init__(self, input_file, output_file):
        super().__init__(input_file, output_file)

    @clocking
    def run(self):
        self._log_header()

        logger.info('loading input file \'{}\''.format(self._input_file))
        wb = xl.load_workbook(self._input_file)
        st = wb.worksheets[0]
        validate_data_dimensions(st)

        cleanser = DataCleanser(st)
        cleanser.trace_mode = self._trace_mode

        cleanser.remove_unnecessary_headers()
        cleanser.reset_column_names()
        cleanser.reset_emplty_values_with_na()

        if self._degree_filter is not None:
            cleanser.filter_records_with_degree(self._degree_filter)

        rule_set_assembler = RuleSetAssembler()
        rule_ids = ['1', '2.1']
        if self._with_rule_2_2:
            rule_ids.append('2.2')
        rule_ids.extend(['3', '4', '5', '6'])
        if self._with_rule_7:
            rule_ids.append('7')
        rule_set = rule_set_assembler.assemble(rule_ids)

        cleanser.apply_rule_set(rule_set)

        validate_data_dimensions(st)

        if self._sheet_tag is not None:
            cleanser.set_sheet_name('cleaned_{}'.format(self._sheet_tag))
        else:
            cleanser.set_sheet_name('cleaned')

        logger.info('writing output file {}'.format(self._output_file))
        wb.save(self._output_file)
        wb.close()

        self._log_tailer()

        return


class DataCleanserStreamRunner(DataCleanserRunner):
    def __init__(self, input_file, output_file):
        super().__init__(input_file, output_file)
        self.__q2c_mapping = {}
        self.__max_column = 0

    def run_part_1(self, tmp_file, salary_value_collector):
        logger.info('loading input file \'{}\''.format(self._input_file))
        in_wb = xl.load_workbook(self._input_file, read_only=True)
        in_ws = in_wb.worksheets[0]
        validate_data_dimensions(in_ws)

        self.__max_column = in_ws.max_column

        out_wb = xl.Workbook(write_only=True)
        out_ws = out_wb.create_sheet()

        filter_chain = FilterChain()
        filter_chain.add_filter(FilterResetColumnNames())
        filter_chain.add_filter(FilterExcludeUnnecessaryHeaders())
        filter_chain.add_filter(FilterOnlyIncludeDegree(self.degree_filter))

        filter_chain.add_filter(FilterExcludeTestRecords())
        filter_chain.add_filter(FilterExcludeRecordWithoutA2Answer())
        if self.with_rule_2_2:
            filter_chain.add_filter(FilterExcludeRecordWithoutSubmitTime())
        filter_chain.add_filter(FilterRinseIrrelevantAnswers(3, RINSE_RULE_IRRELEVANT_QUESTIONS))
        filter_chain.add_filter(FilterRinseNcOptionValues())
        filter_chain.add_filter(FilterRinseInvalidAnswers())

        idx = 0
        for row in in_ws.rows:
            idx += 1

            value_list = self._copy_readonly_cells_to_value_list(row, self.__max_column)

            filter_chain.reset_state()
            filter_chain.do_filter({'idx': idx, 'row': row}, value_list, self.__q2c_mapping)

            if value_list.__len__() > 0:
                out_ws.append(value_list)
                if idx > HEADER_ROW_INDEX:
                    salary_index = self.__q2c_mapping['B6'][0]
                    salary_value = value_list[salary_index]
                    if salary_value is not None:
                        salary_value_collector.collect(int(salary_value))

            if idx % 500 == 0:
                logger.info('>> {} rows processed'.format(idx))

            # if idx > 300:
            #     break

        logger.info('>> {} rows processed in total'.format(idx))

        filter_chain.counter_report()

        logger.info('writing to temp file {}'.format(tmp_file))
        out_wb.save(tmp_file)
        out_wb.close()
        in_wb.close()

    def run_part_2(self, tmp_file, salary_value_collector):
        logger.info('loading temp file \'{}\''.format(tmp_file))
        in_wb = xl.load_workbook(tmp_file, read_only=True)
        in_ws = in_wb.worksheets[0]
        in_ws.calculate_dimension(force=True)
        validate_data_dimensions(in_ws)

        out_wb = xl.Workbook(write_only=True)
        out_ws = out_wb.create_sheet()

        filter_chain = FilterChain()
        salary_filter = FilterRinseUnusualSalaryValues(salary_value_collector)
        filter_chain.add_filter(salary_filter)
        if self.with_rule_7:
            filter_chain.add_filter(FilterRinseIrrelevantAnswers(7, RINSE_RULE_IRRELEVANT_QUESTIONS_V6_COMPATIBLE))

        logger.info(salary_filter.__str__())
        salary_value_collector.report()

        idx = 0
        for row in in_ws.rows:
            idx += 1

            value_list = self._copy_readonly_cells_to_value_list(row, self.__max_column)

            if idx > HEADER_ROW_INDEX:
                filter_chain.reset_state()
                filter_chain.do_filter({'idx': idx, 'row': row}, value_list, self.__q2c_mapping)

            if value_list.__len__() > 0:
                out_ws.append(value_list)

            if idx % 500 == 0:
                logger.info('>> {} rows processed'.format(idx))

        logger.info('>> {} rows processed in total'.format(idx))

        filter_chain.counter_report()

        if self._sheet_tag is not None:
            out_ws.title = 'cleaned_{}'.format(self._sheet_tag)
        else:
            out_ws.title = 'cleaned'

        logger.info('writing output file {}'.format(self._output_file))
        out_wb.save(self._output_file)
        out_wb.close()
        in_wb.close()

    @clocking
    def run(self):
        self._log_header()

        salary_value_collector = SalaryValueCollector()

        temp_file = self._output_file + '.tmp'
        with NamedTemporaryFile(suffix='.xlsx', delete=False) as tmp:
            temp_file = tmp.name

        self.run_part_1(temp_file, salary_value_collector)
        salary_value_collector.lock_down()
        self.run_part_2(temp_file, salary_value_collector)

        os.remove(temp_file)

        self._log_tailer()

        return

    @staticmethod
    def _copy_readonly_cells_to_value_list(row, expected_columns=231):
        value_list = []
        for i in range(0, expected_columns):
            if i < row.__len__():
                value = row[i].value
                if value == '':
                    value = None
            else:
                value = None
            value_list.append(value)
        return value_list


@clocking
def run_single_thread(input_file, degree, tag, setting_groups, trace_mode):
    for setting in setting_groups:
        runner = DataCleanserMemoryRunner(input_file, setting['output_file'])

        if degree is not None:
            runner.degree_filter = degree
        runner.with_rule_2_2 = setting['internal']
        runner.with_rule_7 = setting['analysis']
        runner.sheet_tag = tag
        runner.trace_mode = trace_mode
        runner.run()


@clocking
def run_multi_thread(input_file, degree, tag, setting_groups, trace_mode):

    runners = []
    for setting in setting_groups:

        runner = DataCleanserStreamRunner(input_file, setting['output_file'])

        thread_name = get_thread_name(setting['internal'], setting['analysis'])
        runner.setName(thread_name)

        if degree is not None:
            runner.degree_filter = degree
        runner.with_rule_2_2 = setting['internal']
        runner.with_rule_7 = setting['analysis']
        runner.sheet_tag = tag
        runner.trace_mode = trace_mode

        runner.setDaemon(True)
        runners.append(runner)

    for runner in runners:
        runner.start()
    for runner in runners:
        runner.join()


def get_output_filename(dirpath, name, ext, internal, analysis, tag, degree=None):
    if internal:
        target = 'internal'
    else:
        target = 'public'
    if analysis:
        scope = 'analysis'
    else:
        scope = 'customer'

    if degree is None:
        return os.path.join(dirpath, '{}_cleaned_{}_{}_{}{}'.format(name, target, scope, tag, ext))
    else:
        return os.path.join(dirpath, '{}_cleaned_{}_{}_{}_{}{}'.format(name, degree, target, scope, tag, ext))


def get_error_filename(dirpath, name):
        return os.path.join(dirpath, '{}_error.txt'.format(name))


def get_thread_name(internal, analysis):
    if internal:
        target = 'internal'
    else:
        target = 'public'
    if analysis:
        scope = 'analysis'
    else:
        scope = 'customer'

    return os.path.join('{}-{}'.format(target, scope))

