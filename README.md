# access_logs_search_from_clblog
CW Logs に連携済みのApache/nginxアクセスログをAWS CLBログレコードに基づき検索する

## Usage

```
$ pipenv run ./access_log_search.py --help
usage: access_log_search.py [-h] [-f FILE] [--profile PROFILE]
                            [--region REGION]
                            log_records log_group_name

positional arguments:
  log_records           CLB log records
  log_group_name        CW Logs log group name

optional arguments:
  -h, --help            show this help message and exit
  -f FILE, --file FILE  (Optional) CLB log file
  --profile PROFILE     AWS Profile
  --region REGION       AWS Region
```

### Example

```
$ pipenv run ./access_log_search.py \
--profile oreno_profile --region ap-northeast-1
'2015-05-13T23:39:43.945958Z my-loadbalancer 192.168.131.39:2817 10.0.0.1:80 0.000073 0.001048 0.000057 200 200 0 29 "GET http://www.example.com:80/ HTTP/1.1" "curl/7.38.0" - -
2015-05-13T23:39:43.945958Z my-loadbalancer 192.168.131.39:2817 10.0.0.1:80 0.000086 0.001048 0.001337 200 200 0 57 "GET https://www.example.com:443/ HTTP/1.1" "curl/7.38.0" DHE-RSA-AES128-SHA TLSv1.2' \
'oreno/log/group/name'
```

## 仕様

CLBログの以下項目に基づき検索を行う

- client (IP)
- user_agent
- requestのメソッド
- requestのパス
- requestのHTTPバージョン