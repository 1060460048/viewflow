from viewflow.flow import flow_job, flow_signal


@flow_job()
def dummy_job(flow_task, task):
    pass


def start_process(activation, **kwargs):
    activation.prepare()
    activation.done()


@flow_signal(lambda flow_task, sender: sender.get_task(flow_task))
def do_task(activation, **kwargs):
    activation.prepare()
    activation.done()
