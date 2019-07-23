#!/usr/bin/env python
# -*- coding:utf-8 -*-
import boto3
import argparse
import re
from datetime import (
    datetime,
    timedelta
)


class AccessLogSearch:

    def __init__(self, logs_client, log_group_name: str, log_records: [{}]) -> None:
        self.logs = logs_client
        self.log_group_name = log_group_name
        self.log_records = log_records

    def search_logs(self) -> [[str]]:
        '''
        Description: CloudWatch Logsの検索を行う
        '''
        return [self._filter_log(record) for record in self.log_records]

    def _filter_log(self, log_record: dict) -> [str]:
        '''
        Description ELBログを読み込んでログクエリを投げる
        '''

        start_dt = AccessLogSearch._get_datetime(log_record.get('timestamp'))
        start_end_td = timedelta(minutes=5.0)
        end_dt = start_dt + start_end_td

        pattern = '"' + '" "'.join([
            log_record.get('request_method'),
            log_record.get('request_uri_path'),
            log_record.get('request_http_version'),
            log_record.get('client'),
            log_record.get('user_agent'),
        ]) + '"'

        resp = self.logs.filter_log_events(
            logGroupName=self.log_group_name,
            startTime=int(start_dt.timestamp()) * 1000,  # AWSはミリ秒
            endTime=int(end_dt.timestamp()) * 1000,
            filterPattern=pattern
        )

        return [event.get('message') for event in resp['events']]

    def _get_datetime(date_iso8601: str) -> datetime:
        '''
        Description: ISO 8601形式の時間情報をAWSの使うunix時間(ミリ秒単位)に変換する
        '''
        date_string = date_iso8601
        if 'Z' in date_iso8601:
            date_string = date_iso8601.replace('Z', '+00:00')

        return datetime.fromisoformat(date_string)


class ClbLogPerser:

    _fields = [
        "timestamp",
        "elb",
        "client",
        "client_port",
        "backend",
        "request_processing_time",
        "backend_processing_time",
        "response_processing_time",
        "elb_status_code",
        "backend_status_code",
        "received_bytes",
        "sent_bytes",
        "request",
        "user_agent",
        "ssl_cipher",
        "ssl_protocol",
    ]
    _fields_request = [
        "request_method",  # "request"をさらにパースする
        "request_uri",
        "request_http_version",
    ]
    _fields_uri = [
        "request_uri_scheme",
        "request_uri_host",
        "request_uri_port",
        "request_uri_path"
    ]

    _regex_pattern = '^(.[^ ]*) (.[^ ]*) (.[^ ]*):(\\d*) (.[^ ]*) (.[^ ]*) (.[^ ]*) (.[^ ]*) (.[^ ]*) (.[^ ]*) (\\d*) (\\d*) \"(.*)\" \"(.*)\" (.[^ ]*) (.[^ ]*)'
    _regex = re.compile(_regex_pattern)

    _request_pattern = '^(.[^ ]*) (.[^ ]*) (.[^ ]*)'
    _regex_request = re.compile(_request_pattern)

    _uri_pattern = '^(.[^ ]*)://(.[^ ]*):(\\d*)(.[^ ]*)'
    _regex_uri = re.compile(_uri_pattern)

    def __init__(self, logs: str) -> None:
        '''
        Description: 改行を含むメッセージをパースする
        '''
        self.log_records = [self._parse(record)
                            for record in logs.splitlines()]

    def _parse(self, record: str) -> {}:
        '''
        Description: 1行分のログをパースする
        '''
        parsed_line = self._regex.match(record).groups(0)
        parsed_log = dict(zip(self._fields, parsed_line))

        parsed_request = self._regex_request.match(
            parsed_log['request']).groups(0)
        parsed_log.update(dict(zip(self._fields_request, parsed_request)))

        parsed_uri = self._regex_uri.match(
            parsed_log['request_uri']).groups(0)
        parsed_log.update(dict(zip(self._fields_uri, parsed_uri)))

        return parsed_log

    def parsed_log_records(self) -> []:
        '''
        Description: パースされたメッセージを返す
        '''
        return self.log_records


def get_logs_client(args):
    '''
    Description: boto3クライアントを得る
    '''
    if args.profile:
        session = boto3.Session(profile_name=args.profile)
        return session.client('logs', region_name=args.region)
    else:
        return boto3.client('logs', region_name=args.region)


def main():
    psr = argparse.ArgumentParser()
    psr.add_argument('log_records', help='CLB log records')
    psr.add_argument('log_group_name', help='CW Logs log group name')
    psr.add_argument('-f', '--file', default=None,
                     help='(Optional) CLB log file')
    psr.add_argument('--profile', default=None, help='AWS Profile')
    psr.add_argument('--region', default=None, help='AWS Region')
    args = psr.parse_args()

    if args.file:
        with open(args.file, 'r', encoding='utf-8') as f:
            log_records = ClbLogPerser(f.read())
    else:
        log_records = ClbLogPerser(args.log_records)

    logs = get_logs_client(args)

    searcher = AccessLogSearch(
        logs, args.log_group_name, log_records.parsed_log_records())
    results = searcher.search_logs()

    # sum が flatten をしてくれるらしい
    for line in sum(results, []):
        print(line)


if __name__ == '__main__':
    main()
