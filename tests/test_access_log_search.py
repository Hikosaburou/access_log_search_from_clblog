# -*- coding:utf-8 -*-
import boto3
import pytest
from moto import mock_logs


class TestClbLogPerser(object):
    from access_log_search import ClbLogPerser

    @pytest.fixture
    def sample_log_str(self):
        log_str = '''2015-05-13T23:39:43.945958Z my-loadbalancer 192.168.131.39:2817 10.0.0.1:80 0.000073 0.001048 0.000057 200 200 0 29 "GET http://www.example.com:80/ HTTP/1.1" "curl/7.38.0" - -
2015-05-13T23:39:43.945958Z my-loadbalancer 192.168.131.39:2817 10.0.0.1:80 0.000086 0.001048 0.001337 200 200 0 57 "GET https://www.example.com:443/ HTTP/1.1" "curl/7.38.0" DHE-RSA-AES128-SHA TLSv1.2
'''
        self.ins = self.ClbLogPerser(log_str)

    def test_init_not_none(self, sample_log_str):
        '''
        Description: 正規表現のパースができていることの確認
        '''
        assert None not in self.ins.log_records

    def test_init_keys_request(self, sample_log_str):
        '''
        Description: リクエスト情報が抜き出せることを確認する
        '''
        assert self.ins.log_records[1]['request'] == 'GET https://www.example.com:443/ HTTP/1.1'
        assert self.ins.log_records[1]['request_method'] == 'GET'
        assert self.ins.log_records[1]['request_http_version'] == 'HTTP/1.1'
        assert self.ins.log_records[1]['request_uri'] == 'https://www.example.com:443/'
        assert self.ins.log_records[1]['request_uri_scheme'] == 'https'
        assert self.ins.log_records[1]['request_uri_host'] == 'www.example.com'
        assert self.ins.log_records[1]['request_uri_path'] == '/'


class TestAccessLogSearch:
    from access_log_search import AccessLogSearch
    from access_log_search import ClbLogPerser

    @pytest.fixture
    def sample_log(self):
        log_str = '''2015-05-13T23:39:43.945958Z my-loadbalancer 192.168.132.39:2817 10.0.1.10:80 0.000073 0.001048 0.000057 200 200 0 29 "GET http://www.example.com:80/ HTTP/1.1" "curl/7.38.0" - -
2015-05-13T23:39:43.945958Z my-loadbalancer 192.168.131.39:2817 10.0.0.10:80 0.000086 0.001048 0.001337 200 200 0 57 "GET https://www.example.com:443/ HTTP/1.1" "curl/7.38.0" DHE-RSA-AES128-SHA TLSv1.2
'''
        self.ins = self.ClbLogPerser(log_str)
        self.parsed_logs = self.ins.parsed_log_records()

    @pytest.fixture
    def sample_cwlogs(self):
        with mock_logs():
            conn = boto3.client('logs', 'ap-northeast-1')
            self.log_group_name = 'dummy'
            self.log_stream_name = 'stream'
            conn.create_log_group(logGroupName=self.log_group_name)
            conn.create_log_stream(
                logGroupName=self.log_group_name,
                logStreamName=self.log_stream_name
            )
            messages = [
                {'timestamp': 1431560385000,
                    'message': '10.0.1.10 - - [13/May/2015:08:39:45 +0900] "GET / HTTP/1.1" 200 300 "http://www.example.com/index.html" "curl/7.38.0" "192.168.132.39"'},
                {'timestamp': 1431560385000,
                    'message': '10.0.0.10 - - [13/May/2015:08:39:45 +0900] "GET / HTTP/1.1" 200 985 "https://www.example.com/index.html" "curl/7.38.0" "192.168.131.39"'}
            ]
            conn.put_log_events(
                logGroupName=self.log_group_name,
                logStreamName=self.log_stream_name,
                logEvents=messages
            )
            yield conn

    def test_filter_log(self, sample_log, sample_cwlogs):
        '''
        Description: 1行のログ検索処理に成功する
        '''
        searcher = self.AccessLogSearch(
            logs_client=sample_cwlogs,
            log_group_name=self.log_group_name,
            log_records=self.parsed_logs
        )

        cw_logs = searcher._filter_log(self.parsed_logs[0])
        estimated_results = [
            '10.0.1.10 - - [13/May/2015:08:39:45 +0900] "GET / HTTP/1.1" 200 300 "http://www.example.com/index.html" "curl/7.38.0" "192.168.132.39"',
            '10.0.0.10 - - [13/May/2015:08:39:45 +0900] "GET / HTTP/1.1" 200 985 "https://www.example.com/index.html" "curl/7.38.0" "192.168.131.39"'
        ]

        assert cw_logs == estimated_results

    def test_search_logs(self, sample_log, sample_cwlogs):
        '''
        Description: ELBログ情報を用いて検索する
        '''
        searcher = self.AccessLogSearch(
            logs_client=sample_cwlogs,
            log_group_name=self.log_group_name,
            log_records=self.parsed_logs
        )

        search_results = searcher.search_logs()
        estimated_results = [
            [
                '10.0.1.10 - - [13/May/2015:08:39:45 +0900] "GET / HTTP/1.1" 200 300 "http://www.example.com/index.html" "curl/7.38.0" "192.168.132.39"',
                '10.0.0.10 - - [13/May/2015:08:39:45 +0900] "GET / HTTP/1.1" 200 985 "https://www.example.com/index.html" "curl/7.38.0" "192.168.131.39"'
            ],
            [
                '10.0.1.10 - - [13/May/2015:08:39:45 +0900] "GET / HTTP/1.1" 200 300 "http://www.example.com/index.html" "curl/7.38.0" "192.168.132.39"',
                '10.0.0.10 - - [13/May/2015:08:39:45 +0900] "GET / HTTP/1.1" 200 985 "https://www.example.com/index.html" "curl/7.38.0" "192.168.131.39"'
            ]
        ]
        assert search_results == estimated_results
