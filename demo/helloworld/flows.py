from viewflow import flow, lock
from viewflow.base import this, Flow
from viewflow.contrib import celery
from viewflow.flow import views as flow_views


from .models import HelloWorldProcess
from .tasks import send_hello_world_request


class HelloWorldFlow(Flow):
    """
    Hello world

    This process demonstrates hello world approval request flow.
    """
    process_cls = HelloWorldProcess
    lock_impl = lock.select_for_update_lock

    summary_template = "'{{ process.text }}' message to the world"

    start = (
        flow.Start(
            flow_views.StartFlowView,
            fields=['text'])
        .Permission(auto_create=True)
        .Next(this.approve)
    )

    approve = (
        flow.View(
            flow_views.FlowView, fields=['approved'],
            task_description="Message approvement required",
            task_result_summary="Messsage was {{ process.approved|yesno:'Approved,Rejected' }}")
        .Permission(auto_create=True)
        .Next(this.check_approve)
    )

    check_approve = (
        flow.If(cond=lambda p: p.approved)
        .Then(this.send)
        .Else(this.end)
    )

    send = celery.Job(send_hello_world_request).Next(this.end)

    end = flow.End()
