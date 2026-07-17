from app.jobs.queue import celery_app


def main() -> None:
    celery_app.worker_main(["worker", "--loglevel=INFO", "--queues=report"])


if __name__ == "__main__":
    main()
