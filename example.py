from openscience.arxiv import ArxivDataSource
from openscience import Paper

data_source = ArxivDataSource("/home/science/src")

paper = Paper("1605.00001")
print(paper.load_full_text(data_source))

