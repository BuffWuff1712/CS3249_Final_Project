from typing import TypedDict

from langgraph.graph import END, START, StateGraph

from .catalogue import search_catalogue
from .intent import ShoppingIntent
from .models import Product


class ShoppingState(TypedDict):
    """Data passed between graph nodes."""

    intent: ShoppingIntent
    candidates: list[Product]
    outcome: str


def search_node(state: ShoppingState) -> dict:
    """Search the catalogue using the structured intent."""

    intent = state['intent']
    products = search_catalogue(intent)

    # Return an update rather than mutating state directly.
    return {"candidates": products}


def summarise_node(state: ShoppingState) -> dict:
    """Describe the search result without using an LLM."""

    candidates = state['candidates']

    if len(candidates) > 0:
        outcome = f"Found {len(candidates)} matching products."
    else:
        outcome = "No matching products found."

    return {"outcome": outcome}


def build_workflow():
    """Construct and compile the two-node workflow."""

    builder = StateGraph(ShoppingState)


    builder.add_node('search', search_node)
    builder.add_node('summarise', summarise_node)


    builder.add_edge(START, 'search')
    builder.add_edge('search', 'summarise')
    builder.add_edge('summarise', END)
    
    return builder.compile()


if __name__ == "__main__":
    workflow = build_workflow()

    initial_state: ShoppingState = {
        "intent": ShoppingIntent(
            category="Headphones",
            maximum_price=100,
            currency="SGD",
        ),
        "candidates": [],
        "outcome": "",
    }


    result = workflow.invoke(initial_state)

    print(result["outcome"])
    for product in result["candidates"]:
        print(
            f"- {product.name}: "
            f"{product.currency} {product.price:.2f}"
        )