import unittest
from unittest.mock import patch
from aus_health_forecast.benchmark import benchmark
from aus_health_forecast.contract import ForecastError


class BenchmarkTests(unittest.TestCase):
    def test_invalid_repeats_refused_before_loading(self):
        for n in (True,False,0,4,1.5,'3'):
            with self.subTest(n=n), patch('aus_health_forecast.benchmark.load_series') as load:
                with self.assertRaises(ForecastError): benchmark('unused',n)
                load.assert_not_called()
