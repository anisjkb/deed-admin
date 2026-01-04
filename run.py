import argparse
from src.agents.trend_agent import run_trend_agent

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--agent', choices=['trend'])
    parser.add_argument('--start')
    parser.add_argument('--end')
    parser.add_argument('--format', default='pdf')
    args = parser.parse_args()
    if args.agent == 'trend':
        path = run_trend_agent(start=args.start, end=args.end, format=args.format)
        print(f'Report generated: {path}')

if __name__ == '__main__':
    main()