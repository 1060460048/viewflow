from viewflow.activation import GateActivation
from viewflow.flow.base import Gateway, Edge
from viewflow.token import Token


class DynamicSplitActivation(GateActivation):
    def execute(self):
        self._split_count = self.flow_task._task_count_callback(self.process)

    def activate_next(self):
        if self._split_count:
            token_source = Token.split_token_source(self.task.token, self.task.pk)
            for _ in range(self._split_count):
                self.flow_task._next_task.activate(prev_activation=self, token=next(token_source))


class DynamicSplit(Gateway):
    """
    Activates several outgoing task instances depends on callback value

    Example::

        spit_on_decision = flow.DynamicSplit(lambda p: 4) \\
            .Next(this.make_decision)

        make_decision = flow.View(MyView) \\
            .Next(this.join_on_decision)

        join_on_decision = flow.Join() \\
            .Next(this.end)
    """
    task_type = 'SPLIT'
    activation_cls = DynamicSplitActivation

    def __init__(self, callback):
        super(DynamicSplit, self).__init__()
        self._next_task, self._task_count_callback = None, callback

    def _outgoing(self):
        yield Edge(src=self, dst=self._next_task, edge_class='next')

    def Next(self, node):
        self._next_task = node
        return self


# TODO: Some boilerplate to remove
from viewflow.resolve import resolve_children_links


@resolve_children_links.register(DynamicSplit)
def _(flow_node, resolver):
    flow_node._next_task = resolver.get_implementation(flow_node._next_task)
