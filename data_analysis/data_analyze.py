from data_analysis.data_extract import *
from data_analysis.data_calculate import *
from data_analysis.data_style import *
from data_analysis.result_write import *
from data_analysis.file_loader import *
from data_analysis.analyze_run import *


class DataAnalyzer(object):
    def __init__(self, df):
        self._df = df
        pass

    def analyse(self):
        raise Exception('method not implement')


class ValueRateDataAnalyzer(DataAnalyzer):
    def __init__(self, df, question_col, metric_col):
        super().__init__(df)
        self._question_col = question_col
        self._metric_col = metric_col

    def analyse(self):
        # find out necessary data columns
        ls_metrics_cols = list(CONFIG.BASE_COLUMN)
        if self._question_col not in list(CONFIG.BASE_COLUMN):
            ls_metrics_cols.append(self._question_col)

        # extract data column need to pass to calculators
        de = DataExtractor(self._df)
        df = de.extract_by_col_indexes(ls_metrics_cols)

        result = dict()
        # calculator 1
        result[CONFIG.TOTAL_COLUMN] = OverallRateCalculator(df,
                                                            self._question_col,
                                                            self._metric_col).calculate()
        # calculator 2
        result[CONFIG.GROUP_COLUMN[0]] = GrpRateCalculator(df, self._question_col,
                                                           [CONFIG.BASE_COLUMN[0]]).calculate()
        # calculator 3
        result[CONFIG.GROUP_COLUMN[1]] = GrpRateCalculator(df, self._question_col,
                                                           [CONFIG.BASE_COLUMN[0], CONFIG.BASE_COLUMN[1]]).calculate()

        return result


class WorkOptionDataAnalyzer(ValueRateDataAnalyzer):
    def __init__(self, df):
        super().__init__(df, 'A3','_12')


class NonEmployeeDataAnalyzer(ValueRateDataAnalyzer):
    def __init__(self, df):
        super().__init__(df, 'C1')
        raise Exception('method not implement')


def test():
    # read excel as df
    file_loader=ExcelLoader("../test-data/san-ming/cleaned/cleaned.xlsx")
    df = file_loader.load_data
    # init a result writer
    writer = AnalysisResultWriter(CONFIG.REPORT_FOLDER)
    runner = AnalyzeRunner(writer)

    # Assemble all analyzers need to be run
    analyzer_collection = dict()
    # analyze 1
    analyzer_collection['就业机会'] = WorkOptionDataAnalyzer(df)
    # analyze 2
    #analyzer_collection['未就业分析'] = NonEmployeeDataAnalyzer(df)
    # ... analyze N

    runner.run_batch(analyzer_collection)

    pass


if __name__ == '__main__':
    test()
