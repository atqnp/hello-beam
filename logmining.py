# -*- coding: utf-8 -*-

from __future__ import print_function
import re
import sys
import time
from dateutil.parser import parse as parse_datetime
from dateutil.tz import tzutc

import apache_beam as beam
from apache_beam.options.pipeline_options import PipelineOptions


class Print(beam.PTransform):
    def expand(self, pcoll):
        return pcoll | beam.ParDo(print)


class PrintWindowFn(beam.DoFn):
    def process(self, element, window=beam.DoFn.WindowParam):
        print('%s @ %s' % (window, element))


def extract_timestamp(log):
    mo = re.search(r'\[(.*?)\]', log)
    if mo is not None:
        try:
            dt = parse_datetime(mo.group(0), fuzzy=True)
            dt = dt.astimezone(tzutc())
            return int(time.mktime(dt.timetuple()))
        except Exception:
            pass
    return int(time.time())


class AddTimestampDoFn(beam.DoFn):
    def process(self, element):
        ts = extract_timestamp(element)
        yield beam.window.TimestampedValue(element, ts)


options = PipelineOptions()
with beam.Pipeline(options=options) as p:
    lines = p | 'create' >> beam.io.ReadFromText('access.log')
    windowed_counts = (
        lines
        | 'timestamp' >> beam.ParDo(AddTimestampDoFn())
        | 'window' >> beam.WindowInto(beam.window.FixedWindows(1800)) # 30 minutes
        | 'count' >> beam.CombineGlobally(beam.combiners.CountCombineFn()).without_defaults()
    )
    windowed_counts =  windowed_counts | beam.ParDo(PrintWindowFn())
