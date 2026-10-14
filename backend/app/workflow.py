"""The single shopping graph: search, propose, review, simulated checkout."""
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph

from .checkout import CheckoutState, ReceiptStore, checkout_node, route_after_human_review
from .review import human_review_node, prepare_review_node, route_after_policy
from .shopping_nodes import check_policy_node, propose_node, search_node, summarise_node


def build_workflow(store: ReceiptStore):
    """Compile once; reuse this graph and thread ID when resuming a run.

    Receipts and checkpoints are in memory and are lost on process exit.
    The shared receipt store is a dependency, not checkpoint state.
    """
    builder = StateGraph(CheckoutState)
    builder.add_node('search', search_node)
    builder.add_node('propose', propose_node)
    builder.add_node('check_policy', check_policy_node)
    builder.add_node('summarise', summarise_node)
    builder.add_node('prepare_review', prepare_review_node)
    builder.add_node('human_review', human_review_node)
    builder.add_node('checkout', lambda state: checkout_node(state, store))

    builder.add_edge(START, 'search')
    builder.add_edge('search', 'propose')
    builder.add_edge('propose', 'check_policy')
    builder.add_conditional_edges('check_policy', route_after_policy, {
        'summarise': 'summarise', 'prepare_review': 'prepare_review',
    })
    builder.add_edge('summarise', END)
    builder.add_edge('prepare_review', 'human_review')
    builder.add_conditional_edges('human_review', route_after_human_review, {
        'approved': 'checkout', 'not_approved': END,
    })
    builder.add_edge('checkout', END)
    return builder.compile(checkpointer=InMemorySaver())
