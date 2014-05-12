from django.contrib import admin
from viewflow.admin import ProcessAdmin, TaskAdmin
from examples.helloworld import models, flows


@admin.register(models.HelloWorldProcess)
class HelloWorldProcessAdmin(ProcessAdmin):
    list_display = ['pk', 'created', 'get_status_display', 'participants',
                    'text', 'approved']
    list_display_links = ['pk', 'created']


@admin.register(models.HelloWorldTask)
class HelloWorldTaskAdmin(TaskAdmin):
    list_display = ['pk', 'created', 'get_status_display',
                    'owner', 'owner_permission', 'token',
                    'started', 'finished']
    list_display_links = ['pk', 'created']

    def get_queryset(self, request):
        qs = super(HelloWorldTaskAdmin, self).get_queryset(request)
        return qs.filter(process__flow_cls=flows.HelloWorldFlow)
