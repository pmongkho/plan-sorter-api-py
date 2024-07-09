import json
import re
import pdfplumber
from collections import defaultdict
from PyPDF2 import PdfReader, PdfWriter
from pathlib import Path
import time

class PdfPlanSorter:
    def __init__(self):
        self.weights_file_path = 'plan_weights.pdf'
        self.batches_file_path = 'plan_batches.pdf'
        self.weights_plans_and_pages = {}
        self.batches_plans_and_pages = {}
        self.dictionary = {}

    def txt_to_array(self, file_path):
        """
        Read the contents of an order file and return a list of stripped lines.

        Parameters:
            file_path (str): The path to the order file.

        Returns:
            list: A list containing the stripped lines of the file.
        """
        orders = []
        with open(file_path, "r") as order_file:
            for line in order_file:
                stripped_line = line.strip()
                orders.append(stripped_line)
            list(set(orders))
        return orders

    def extract_weights_plans_and_pages(self):
        weights_plan_number_re = re.compile(r'^2\d{6}')
        weights_page_number_re = re.compile(r'(Page)\s\-\s([0-9]+)')
        plan_pattern = re.compile(r'(\d{7})')
        component_pattern = re.compile(r'(?<=310\s(?:40\.00|75\.00)\s)(\w+)(?:/\d+)?')
        quantity_pattern = re.compile(r'(\d+)(?=\.\d+\s*LB)')

        with pdfplumber.open(self.weights_file_path) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                for line in text.split('\n'): 
                    page_match = weights_page_number_re.search(line)
                    plan_match = weights_plan_number_re.search(line)

                    # Assuming 'line' is the current line you're processing
                    component_match = component_pattern.search(line)
                    quantity_match = quantity_pattern.search(line)
                    
                    if page_match:
                        found_page = page_match.group(2)
                    elif plan_match:
                        found_plan = plan_match.group()
                        self.weights_plans_and_pages[found_page] = found_plan
                        
                        # Extract the matched strings
                        plan_key = plan_match.group()
                        component_value = component_match.group() if component_match else None
                        quantity_value = quantity_match.group() if quantity_match else 0
                        
                        if component_value is not None:
                        # Check if the plan_key already exists in the dictionary
                            
                            if plan_key in self.dictionary:
                            # Append to the existing list associated with plan_key
                                self.dictionary[plan_key].append({component_value: int(quantity_value)})
                            else:
                                # Create a new list with the first entry for plan_key
                                self.dictionary[plan_key] = [{component_value: int(quantity_value)}]

    def extract_batches_plans_and_pages(self):
        batches_plan_number_re = re.compile(r'(Production Plan)\s\:\s([0-9]+)')
        batches_page_number_re = re.compile(r'(Page)\s\:\s([0-9]+)')
        flex_list_re = re.compile(r'(Production Plan)(.*)(Pouch)')
        batch_number_re = re.compile(r"Totals:\s*(\d+(\.\d+)?)")

        with pdfplumber.open(self.batches_file_path) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                for line in text.split('\n'):
                    # Check for flex
                    flex_match = flex_list_re.search(line)
                    if flex_match:
                        continue

                    # Extract page and plan numbers
                    page_match = batches_page_number_re.search(line)
                    plan_match = batches_plan_number_re.search(line)
                    batch_total = batch_number_re.search(line)
                    if page_match:
                        found_page = page_match.group(2)
                    elif plan_match:
                        found_plan = plan_match.group(2)
                        self.batches_plans_and_pages[found_page] = found_plan
                        if found_plan in self.dictionary:
                            self.dictionary[found_plan].append(batch_total)

    def combine_plans_and_pages(self):
        combined_plans_with_pages = defaultdict(list)
        for d in (self.weights_plans_and_pages, self.batches_plans_and_pages):
            for key, value in d.items():
                combined_plans_with_pages[value].append(key) 
        return combined_plans_with_pages

    def add_pages_to_pdf(self, can1, hydro, line3, combined_plans_with_pages):
        weights_input_pdf = PdfReader(self.weights_file_path)
        batches_input_pdf = PdfReader(self.batches_file_path)
        pdf_writer = PdfWriter()

        for items_list in [can1, hydro, line3]:
            pdf_writer.add_blank_page(width=792, height=612)  # Standard US Letter size
            for items in items_list:
                try:
                    findpage2 = int(combined_plans_with_pages[items][1]) - 1
                    findpage1 = int(combined_plans_with_pages[items][0]) - 1
                    page2 = batches_input_pdf.pages[findpage2]
                    pdf_writer.add_page(page2)
                    page = weights_input_pdf.pages[findpage1]
                    pdf_writer.add_page(page)
                except:
                    continue
            # Add a blank page



        with Path("plans_in_order.pdf").open(mode="wb") as output_file:
            pdf_writer.write(output_file)

    def process_plan_sort(self):
        # Read orders from files
        can1 = self.txt_to_array("order_can1.txt")
        hydro = self.txt_to_array("order_hydro.txt")
        line3 = self.txt_to_array("order_line3.txt")

        # Extract plans and pages from PDFs
        self.extract_weights_plans_and_pages()
        self.extract_batches_plans_and_pages()

        # json_data = json.dumps(self.dictionary, indent=8)

        # # Print or use the JSON data
        # print(json_data)

        # Function to print JSON data letter by letter
        # def print_json_letter_by_letter(data):
        #     json_str = json.dumps(data, indent=4)  # Convert JSON to string with indentation for readability
        #     for char in json_str:
        #         print(char, end='', flush=True)
        #         time.sleep(0.005)  # Adjust delay as needed for desired speed
        #     print()  # Move to next line after complete output

        # Call the function to print JSON self.dictionary letter by letter
        # print_json_letter_by_letter(self.dictionary)
       
        # Combine plans and pages
        combined_plans_with_pages = self.combine_plans_and_pages()
        # print(combined_plans_with_pages)

        # Add pages to PDF
        self.add_pages_to_pdf(can1, hydro, line3, combined_plans_with_pages)

# Usage:
pdf_plan_sorter = PdfPlanSorter()
pdf_plan_sorter.process_plan_sort()
