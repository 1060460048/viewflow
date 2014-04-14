from django.utils.decorators import classonlymethod


class Activation(object):
    """
    Activation responsible for managing state and persistance of task instance

    There is no common interface for activation, but every subactivation type
    defines each own
    """
    def __init__(self, **kwargs):
        """
        Activation should be available for instante without any constructor parameters.
        """
        super(Activation, self).__init__(**kwargs)


class StartActivation(Activation):
    """
    Base activation that starts new process instance
    """
    def __init__(self, **kwargs):
        self.flow_cls, self.flow_task = None, None
        self.process, self.task = None, None
        super(StartActivation, self).__init__(**kwargs)

    def initialize(self, flow_task):
        """
        Initialize new activation instance
        """
        self.flow_task, self.flow_cls = flow_task, flow_task.flow_cls

        self.process = self.flow_cls.process_cls(flow_cls=self.flow_cls)
        self.task = self.flow_cls.task_cls(process=self.process, flow_task=self.flow_task)

    def prepare(self):
        self.task.prepare()

    def save_process(self):
        """
        Save process when done,
        """
        self.process.save()
        return self.process

    def done(self, process=None):
        """
        Creates and starts new process instance
        """
        if process:
            self.process = process
        self.process = self.save_process()

        self.task.process = process
        self.task.done()
        self.task.save()

        self.process.start()
        self.process.save()

        self.flow_task.activate_next(self)


class ViewActivation(Activation):
    """
    Base activation that starts new process instance
    """
    def __init__(self, **kwargs):
        self.flow_cls, self.flow_task = None, None
        self.process, self.task = None, None
        super(ViewActivation, self).__init__(**kwargs)

    def initialize(self, flow_task, task):
        """
        Initialize new activation instance
        """
        self.flow_task, self.flow_cls = flow_task, flow_task.flow_cls

        self.process = self.flow_cls.process_cls._default_manager.get(flow_cls=self.flow_cls, pk=task.process_id)
        self.task = task

    def assign(self, user):
        self.task.assign(user=user)
        self.task.save()

    def prepare(self):
        self.task.prepare()

    def get_task(self):
        return self.task

    def done(self):
        self.task = self.get_task()
        self.task.done()
        self.task.save()

        self.flow_task.activate_next(self)

    @classmethod
    def activate(cls, flow_task, prev_activation):
        flow_cls, flow_task = flow_task.flow_cls, flow_task
        process = prev_activation.process

        task = flow_cls.task_cls(
            process=process,
            flow_task=flow_task)

        # Try to assign permission
        owner_permission = flow_task.calc_owner_permission(task)
        if owner_permission:
            task.owner_permission = owner_permission

        task.save()
        task.previous.add(prev_activation.task)

        activation = cls()
        activation.initialize(flow_task, task)

        # Try to assign owner
        owner = flow_task.calc_owner(task)
        if owner:
            activation.assign(owner)

        return activation


class EndActivation(Activation):
    def initialize(self, flow_task, task):
        """
        Initialize new activation instance
        """
        self.flow_task, self.flow_cls = flow_task, flow_task.flow_cls

        self.process = self.flow_cls.process_cls._default_manager.get(flow_cls=self.flow_cls, pk=task.process_id)
        self.task = task

    def prepare(self):
        self.task.prepare()

    def done(self):
        self.task.done()
        self.task.save()

        self.process.finish()
        self.process.save()

        for task in self.process.active_tasks():
            task.flow_task.deactivate(task)

    @classmethod
    def activate(cls, flow_task, prev_activation):
        flow_cls, flow_task = flow_task.flow_cls, flow_task
        process = prev_activation.process

        task = flow_cls.task_cls(
            process=process,
            flow_task=flow_task)

        task.save()
        task.previous.add(prev_activation.task)

        activation = cls()
        activation.initialize(flow_task, task)
        activation.prepare()
        activation.done()

        return activation
