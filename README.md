

## Quick start
Change environment variables in `.env` file.

```console
~$ source .env
~$ chmod +x ./percentil.py
~$ ./percentil.py -f "2023-09-14 02:37:00" -u "2023-09-14 02:45:00"
```

## Usage
```console
usage: percentil.py [-h] -f F -u U

Calculate the 95th percentile for the dashboard graphs.

options:
  -h, --help  show this help message and exit
  -f F        from date, format "Year-Month-Day Hour:Min:Sec", example 2023-09-13 14:30:00
  -u U        until date, format "Year-Month-Day Hour:Min:Sec", example 2023-09-13 14:30:00
```