.PHONY: tunnel server worker all
tunnel:
	cloudflared tunnel run printer

server:
	uv run fastapi run printer/server.py

worker:
	uv run printer/worker.py

all:
	$(MAKE) worker &
	$(MAKE) server &
	$(MAKE) tunnel &
