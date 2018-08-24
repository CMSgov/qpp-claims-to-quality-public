"""Utility functions for posting messages using the Slack API."""
# TODO: Use Python requests instead of curl.
import subprocess

from claims_to_quality.config import config


def post_to_slack(message):
    """Function to post message to Slack."""
    url = config.get('slack.url')
    post = ('curl -X POST -H \'Content-type: application/json\' '
            '--data \'{{"text":"{message}"}}\' '
            '{url}')
    post = post.format(url=url, message=message)
    subprocess.call(args=[post], shell=True)


def post_to_slack_tagging_here(message):
    """Function to post message to Slack, including the @here tag."""
    url = config.get('slack.url')
    post = ('curl -X POST -H \'Content-type: application/json\' '
            '--data \'{{"text":"<!here> {message}"}}\' '
            '{url}')
    post = post.format(url=url, message=message)
    subprocess.call(args=[post], shell=True)
