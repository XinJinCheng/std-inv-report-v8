#!/usr/bin/env python3
# -*- coding: utf-8 -*-

'formulas.py'

__author__ = 'kuoren'

import pandas as pd
import numpy as np
import data_analysis.config as CONFIG
import data_analysis.utils as Util
from data_cleansing.logging import *

logger = get_logger(__name__)


def formula_rate(data, subject):
    """

    AnswerRate 计算某题的答案占比
    :param data: 数据
    :param subject: 题号
    :return: '答案', '比例', '答题总人数',
    """

    # 答题总人数
    count = data[subject].count()
    # 答案占比
    df_rate = data[subject].value_counts()
    df_rate = pd.DataFrame({CONFIG.RATE_COLUMN[0]: df_rate.index,
                            CONFIG.RATE_COLUMN[1]: df_rate.values,
                            CONFIG.RATE_COLUMN[-1]: df_rate.values / count
                            })
    df_rate[CONFIG.RATE_COLUMN[2]] = count
    print(df_rate)
    return df_rate


def formula_rate_grp(data, subject, grp):
    """

    AnswerRateGrp：分组计算某题的答案占比
    :param data:
    :param subject:
    :param grp:
    :return:
    """

    # 分组算总数
    df_count = data.groupby(grp)[subject].count()
    # 分组算各答案分布
    sub_grp = grp.copy()
    sub_grp.append(subject)
    df_rate = data.groupby(sub_grp)[subject].count().unstack(fill_value=0)
    # 计算比例
    df_rate = df_rate.apply(lambda x: x / df_count)
    df_rate[CONFIG.RATE_COLUMN[2]] = df_count
    df_rate.fillna(0, inplace=True)
    df_rate.sort_values(CONFIG.RATE_COLUMN[2], ascending=0, inplace=True)
    df_rate.reset_index(inplace=True)
    return df_rate


def formula_five_rate(data, subject, measure_type):
    """
    五维占比
    :param data:
    :param subject:
    :param measure_type:
    :return:
    """
    # step1：各个答案占比
    df_rate = formula_rate(data, subject)
    # 行转列
    df_t = formate_rate_t(df_rate)
    # 相关度/满意度/符合度
    ls_measure = parse_measure(measure_type)
    dict_measure_score = parse_measure_score(measure_type)
    measure_name = parse_measure_name(measure_type)
    # 列重排
    df_t = df_t[ls_measure[0:5]]
    # step3: 度量值
    measure_rate = 0
    for measure in ls_measure[0:3]:
        measure_rate = measure_rate + df_t[measure]
    df_t[measure_name] = measure_rate

    # step4: 均值
    mean = data[subject].map(dict_measure_score).mean()
    df_t[CONFIG.MEAN_COLUMN[-1]] = mean
    df_t[CONFIG.MEAN_COLUMN[2]] = df_rate.loc[0, CONFIG.RATE_COLUMN[2]]

    return df_t


def formula_five_rate_grp(data, subject, grp, measure_type):
    """
    分组计算某题的五维占比
    :param data:
    :param subject:
    :param grp:
    :return:
    """

    # 答案占比
    df_rate = formula_rate_grp(data, subject, grp)
    # 相关度/满意度/符合度
    ls_measure = parse_measure(measure_type)
    dict_measure_score = parse_measure_score(measure_type)
    measure_name = parse_measure_name(measure_type)
    # 列重排
    df_sub = df_rate[ls_measure[0:5]]
    # step3: 度量值
    measure_rate = 0
    for measure in ls_measure[0:3]:
        measure_rate = measure_rate + df_rate[measure]
    df_sub[measure_name] = measure_rate

    data["measure_score"] = data[subject].map(dict_measure_score)
    df_mean = data.groupby(grp)["measure_score"].mean()
    df_sub[CONFIG.MEAN_COLUMN[-1]] = df_mean
    df_sub[CONFIG.MEAN_COLUMN[2]] = df_rate[CONFIG.MEAN_COLUMN[2]]
    df_sub.fillna(0, inplace=True)
    df_sub.sort_values(CONFIG.RATE_COLUMN[2], ascending=0, inplace=True)
    df_sub.reset_index(inplace=True)
    return df_sub


def formula_employe_rate(data):
    '''

    Employe rate:就业率
    公式：（就业人数-未就业人数）/答题总人数
    :param data:
    :return: 就业率 答题总人数
    '''
    subject = 'A2'

    # step1:答题总人数
    count = data[subject].count()

    # step2:回答"未就业"人数
    unemployee_count = data[data[subject] == CONFIG.A2_ANSWER[-1]][subject].count()

    employee_rate = ((count - unemployee_count) / count).round(decimals=CONFIG.DECIMALS6)
    # 就业率 答题总人数
    pd_result = pd.DataFrame({CONFIG.EMPLOYEE_RATE_COLUMN: [employee_rate],
                              CONFIG.RATE_COLUMN[2]: [count]})
    print(pd_result)
    return pd_result


def formula_employe_rate_grp(data, array_grps):
    """
    Employe rate:各学院\专业\其他分组 就业率
    :param data:
    :param array_grps: 分组
    :return:
    """
    subject = 'A2'

    # step1:各分组 答题总人数
    df_count = data.groupby(array_grps)[subject].count()
    # step2:各分组 回答"未就业"人数
    df_unemployee = data[data[subject] == CONFIG.A2_ANSWER[-1]].groupby(array_grps)[subject].count()
    df_rate = (df_count - df_unemployee) / df_count
    # 就业率 答题总人数
    df_merge = pd.DataFrame({CONFIG.EMPLOYEE_RATE_COLUMN: df_rate,
                             CONFIG.RATE_COLUMN[2]: df_count})
    df_merge.fillna(0, inplace=True)
    df_merge.sort_values(CONFIG.RATE_COLUMN[2], ascending=0, inplace=True)
    print(df_merge)
    return df_merge


def formula_income_mean(data):
    '''

    Income mean:薪酬均值
    ****此公式包含默认的前提：A2=在国内工作
    公式：薪酬总和/答题总人数
    :param data:
    :return: 均值 答题总人数
    '''
    subject = 'B6'
    # 前提要素
    df_primise = data[data['A2'] == CONFIG.A2_ANSWER[0]]

    # 均值 答题总人数
    df_mean = pd.DataFrame({CONFIG.MEAN_COLUMN[-1]: [df_primise[subject].mean()],
                            CONFIG.MEAN_COLUMN[2]: [df_primise[subject].count()]})
    return df_mean


def formula_mean_grp(data, subject, grp):
    """
    分组计算均值
    :param data:
    :param subject:
    :param grp:
    :return: 均值、答题总人数
    """
    df_count = data.groupby(grp)[subject].count()
    df_mean = data.groupby(grp)[subject].mean()
    df_result = pd.DataFrame({CONFIG.MEAN_COLUMN[-1]: df_mean,
                              CONFIG.MEAN_COLUMN[2]: df_count})
    df_result.sort_values(CONFIG.RATE_COLUMN[2], ascending=0, inplace=True)
    return df_result


def formate_rate_t(df_data):
    """格式化：总体比率行转列"""
    if df_data.empty:
        return df_data
    # 答题总人数
    count = df_data.loc[0, CONFIG.RATE_COLUMN[2]]

    # 比例转置
    df_t = df_data.pivot_table(CONFIG.RATE_COLUMN[-1], index=None,
                               columns=CONFIG.RATE_COLUMN[0])
    df_t[CONFIG.RATE_COLUMN[2]] = count
    print(df_t)
    return df_t


def major_row_combine(df_data, array_focus=[CONFIG.MEAN_COLUMN[2]], combin_name=CONFIG.COMBINE_RATE):
    if df_data.empty:
        return df_data

    # 非合并列 学院、专业、答题总人数
    ls_focus = array_focus.copy()
    ls_focus.append(CONFIG.GROUP_COLUMN[0])
    ls_focus.append(CONFIG.GROUP_COLUMN[1])
    df_summary = df_data.loc[:, ls_focus]
    df_duplicate = df_summary.drop_duplicates()

    # 多列合并单列
    df_combine = df_data.loc[:,
                 [CONFIG.GROUP_COLUMN[0], CONFIG.GROUP_COLUMN[1], CONFIG.RATE_COLUMN[0], CONFIG.RATE_COLUMN[-1]]]
    df_combine['answer_rate'] = df_combine[CONFIG.RATE_COLUMN[0]].astype(str) + '(' + (df_combine[
                                                                                           CONFIG.RATE_COLUMN[
                                                                                               -1]] * 100).map(
        lambda x: '%.2f%%' % x) + ')'
    df_combined = df_combine.loc[:, [CONFIG.GROUP_COLUMN[0], CONFIG.GROUP_COLUMN[1], 'answer_rate']]
    df_combined.rename(columns={'answer_rate': combin_name}, inplace=True)
    df_row_combine = df_combined.groupby([CONFIG.GROUP_COLUMN[0], CONFIG.GROUP_COLUMN[1]],
                                         as_index=False).aggregate(
        lambda x: ';'.join(list(x)))
    # 转置合并 ';'.join(list(df_combined.loc[:, combin_name]))
    df_result = pd.merge(df_row_combine, df_duplicate, how='left', on=[CONFIG.GROUP_COLUMN[0], CONFIG.GROUP_COLUMN[1]])
    df_result.sort_values(CONFIG.MEAN_COLUMN[2], ascending=0, inplace=True)

    return df_result


def college_row_combine(df_data, array_focus=[CONFIG.MEAN_COLUMN[2]], combin_name=CONFIG.COMBINE_RATE):
    if df_data.empty:
        return df_data

    # 非合并列 学院、答题总人数
    ls_focus = array_focus.copy()
    ls_focus.append(CONFIG.GROUP_COLUMN[0])
    df_summary = df_data.loc[:, ls_focus]
    df_duplicate = df_summary.drop_duplicates()

    # 多列合并单列
    df_combine = df_data.loc[:,
                 [CONFIG.GROUP_COLUMN[0], CONFIG.RATE_COLUMN[0], CONFIG.RATE_COLUMN[-1]]]
    df_combine['answer_rate'] = df_combine[CONFIG.RATE_COLUMN[0]].astype(str) + '(' + (df_combine[
                                                                                           CONFIG.RATE_COLUMN[
                                                                                               -1]] * 100).map(
        lambda x: '%.2f%%' % x) + ')'
    df_combined = df_combine.loc[:, [CONFIG.GROUP_COLUMN[0], 'answer_rate']]
    df_combined.rename(columns={'answer_rate': combin_name}, inplace=True)
    df_row_combine = df_combined.groupby(CONFIG.GROUP_COLUMN[0],
                                         as_index=False).aggregate(
        lambda x: ';'.join(list(x)))
    # 转置合并
    df_result = pd.merge(df_row_combine, df_duplicate, how='left', on=CONFIG.GROUP_COLUMN[0])
    df_result.sort_values(CONFIG.MEAN_COLUMN[2], ascending=0, inplace=True)
    return df_result



def row_combine(df_data, array_focus=[CONFIG.MEAN_COLUMN[2]], combin_name=CONFIG.COMBINE_RATE):
    if df_data.empty:
        return df_data

    # 非合并列、答题总人数
    df_summary = df_data.loc[:, array_focus]
    df_duplicate = df_summary.drop_duplicates()

    # 多列合并单列
    df_combine = df_data.loc[:,
                 [CONFIG.RATE_COLUMN[0], CONFIG.RATE_COLUMN[-1]]]
    df_combine['answer_rate'] = df_combine[CONFIG.RATE_COLUMN[0]].astype(str) + '(' + (df_combine[
                                                                                           CONFIG.RATE_COLUMN[
                                                                                               -1]] * 100).map(
        lambda x: '%.2f%%' % x) + ')'
    df_combined = df_combine.loc[:, ['answer_rate']]
    df_combined.rename(columns={'answer_rate': combin_name}, inplace=True)
    row_combine = ';'.join(list(df_combined.loc[:, combin_name]))
    df_duplicate.insert(0, combin_name, row_combine)
    return df_duplicate


def answer_period(data, subject, start, end, step):
    ind_500 = list(range(start, end + step, step))

    ind_500.insert(0, 0)
    ind_500.append(100000)

    income = data['B6']
    counts = income.count()
    period = pd.cut(income.values, ind_500)
    period_counts = period.value_counts()
    pd_period = pd.DataFrame({CONFIG.RATE_COLUMN[0]: period_counts.index,
                              CONFIG.RATE_COLUMN[1]: period_counts.values})
    pd_period[CONFIG.RATE_COLUMN[-1]] = (pd_period[CONFIG.RATE_COLUMN[1]] / counts).round(decimals=CONFIG.DECIMALS6)
    pd_period[CONFIG.RATE_COLUMN[2]] = counts

    return pd_period


def percent(df_data):
    if df_data.empty:
        return df_data
    columns = [col for col in df_data.columns]
    elimite_cols = [CONFIG.MEAN_COLUMN[2], CONFIG.MEAN_COLUMN[-1],
                    CONFIG.MEAN_COLUMN[1], CONFIG.MEAN_COLUMN[0],
                    CONFIG.GROUP_COLUMN[0], CONFIG.GROUP_COLUMN[1], CONFIG.ABILITY_COLUMN,
                    CONFIG.GROUP_COLUMN[2], CONFIG.TOTAL_COLUMN]
    for column in elimite_cols:
        if column in columns:
            columns.remove(column)
    df_data.loc[:, columns] = df_data.loc[:, columns].applymap(lambda x: '%.2f%%' % x)

    return df_data


def parse_measure(measure_type):
    if CONFIG.ANSWER_TYPE_MEET == measure_type:
        return CONFIG.ANSWER_NORMAL_MEET
    elif CONFIG.ANSWER_TYPE_RELATIVE == measure_type:
        return CONFIG.ANSWER_NORMAL_RELATIVE
    elif CONFIG.ANSWER_TYPE_SATISFY == measure_type:
        return CONFIG.ANSWER_NORMAL_SATISFY
    elif CONFIG.ANSWER_TYPE_IMPORTANT == measure_type:
        return CONFIG.ANSWER_NORMAL_IMPORTANT
    elif CONFIG.ANSWER_TYPE_PLEASED == measure_type:
        return CONFIG.ANSWER_NORMAL_PLEASED
    elif CONFIG.ANSWER_TYPE_MEET_V == measure_type:
        return CONFIG.ANSWER_NORMAL_MEET_V
    elif CONFIG.ANSWER_TYPE_HELP == measure_type:
        return CONFIG.ANSWER_NORMAL_HELP
    elif CONFIG.ANSWER_TYPE_FEEL == measure_type:
        return CONFIG.ANSWER_NORMAL_FEEL
    elif CONFIG.ANSWER_TYPE_NUM == measure_type:
        return CONFIG.ANSWER_NORMAL_NUM


def parse_measure_name(measure_type):
    if CONFIG.ANSWER_TYPE_MEET == measure_type:
        return CONFIG.MEASURE_NAME_MEET
    elif CONFIG.ANSWER_TYPE_RELATIVE == measure_type:
        return CONFIG.MEASURE_NAME_RELATIVE
    elif CONFIG.ANSWER_TYPE_SATISFY == measure_type:
        return CONFIG.MEASURE_NAME_SATISFY
    elif CONFIG.ANSWER_TYPE_IMPORTANT == measure_type:
        return CONFIG.MEASURE_NAME_IMPORTANT
    elif CONFIG.ANSWER_TYPE_PLEASED == measure_type:
        return CONFIG.MEASURE_NAME_PLEASED
    elif CONFIG.ANSWER_TYPE_MEET_V == measure_type:
        return CONFIG.MEASURE_NAME_MEET_V
    elif CONFIG.ANSWER_TYPE_HELP == measure_type:
        return CONFIG.MEASURE_NAME_HELP
    elif CONFIG.ANSWER_TYPE_FEEL == measure_type:
        return CONFIG.MEASURE_NAME_FEEL
    elif CONFIG.ANSWER_TYPE_NUM == measure_type:
        return CONFIG.MEASURE_NAME_NUM
    else:
        return measure_type


def parse_measure_score(measure_type):
    if CONFIG.ANSWER_TYPE_MEET == measure_type:
        return CONFIG.ANSWER_SCORE_DICT_MEET
    elif CONFIG.ANSWER_TYPE_RELATIVE == measure_type:
        return CONFIG.ANSWER_SCORE_DICT_RELATIVE
    elif CONFIG.ANSWER_TYPE_SATISFY == measure_type:
        return CONFIG.ANSWER_SCORE_DICT_SATISFY
    elif CONFIG.ANSWER_TYPE_IMPORTANT == measure_type:
        return CONFIG.ANSWER_SCORE_DICT_IMPORTANT
    elif CONFIG.ANSWER_TYPE_PLEASED == measure_type:
        return CONFIG.ANSWER_SCORE_DICT_PLEASED
    elif CONFIG.ANSWER_TYPE_MEET_V == measure_type:
        return CONFIG.ANSWER_SCORE_DICT_MEET_V
    elif CONFIG.ANSWER_TYPE_HELP == measure_type:
        return CONFIG.ANSWER_SCORE_DICT_HELP
    elif CONFIG.ANSWER_TYPE_FEEL == measure_type:
        return CONFIG.ANSWER_SCORE_DICT_FEEL
    elif CONFIG.ANSWER_TYPE_NUM == measure_type:
        return CONFIG.ANSWER_SCORE_DICT_NUM
