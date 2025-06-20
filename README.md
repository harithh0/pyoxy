# Pyoxy

A lightweight HTTP/HTTPS proxy written in Python. Supports both IPv4 and IPv6 with proper request rewriting, header handling, and `CONNECT` tunneling for HTTPS.

## Features

- HTTP request rewriting (removes proxy-specific headers, reformats request line)
- HTTPS support via `CONNECT` method tunneling
- Dual stack: IPv4 and IPv6 startup scripts
- Request logging to `requests.log`
- Graceful error handling with meaningful responses

## Files

- `pyoxy.py`: Core proxy server logic
- `start_proxy_v4.py`: Starts proxy using IPv4 (127.0.0.1)
- `start_proxy_v6.py`: Starts proxy using IPv6 (::1)

## Usage

- Change the address and port information in these files first

```bash
# Run IPv4 proxy
python3 start_proxy_v4.py

# Or run IPv6 proxy
python3 start_proxy_v6.py
```

Then configure your browser or CLI tools to use the proxy:

```bash
curl -x http://127.0.0.1:2222 http://example.com
curl -6 -x http://[::1]:2226 http://example.com
```

## Notes

- HTTPS traffic is tunneled (not decrypted or inspected).
- Logs are written to `requests.log`.

## Future features

- TLS support so client can the proxy through HTTPs (be more secure)
- Ability to see encrypted traffic between client and HTTPs target
- Input validate raw connection to socket (not through `curl` or proxy client)

## License

MIT

