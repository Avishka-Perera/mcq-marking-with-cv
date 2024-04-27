from tkinter.ttk import Frame, Label, Entry, Button
from tkinter import Tk, END, BOTTOM, LEFT, RIGHT
from tkinter import filedialog

from utils import markMCQ


class App(Tk):
    def __init__(self):
        super().__init__()
        framePaddings = {"padx": 10, "pady": 10}
        paddings = {"padx": 5, "pady": 5}
        entry_font = {"font": ("Helvetica", 11)}
        fileSelFrame = Frame(self)
        fileSelFrame.pack(**framePaddings)

        correctAnsLabel = Label(fileSelFrame, text="Correct answers file")
        correctAnsEntry = Entry(fileSelFrame, width=60, **entry_font)
        correctAnsSelBtn = Button(
            fileSelFrame,
            text="Select",
            command=lambda: self.browseFiles(correctAnsEntry, [1]),
        )
        correctAnsLabel.grid(sticky="W", row=2, column=0, **paddings)
        correctAnsEntry.grid(row=2, column=1, **paddings)
        correctAnsSelBtn.grid(row=2, column=2, **paddings)

        ansSheetLabel = Label(fileSelFrame, text="Answer sheet pdf")
        ansSheetEntry = Entry(fileSelFrame, width=60, **entry_font)
        ansSheetSelBtn = Button(
            fileSelFrame,
            text="Select",
            command=lambda: self.browseFiles(ansSheetEntry, [2]),
        )
        ansSheetLabel.grid(sticky="W", row=4, column=0, **paddings)
        ansSheetSelBtn.grid(row=4, column=2, **paddings)
        ansSheetEntry.grid(row=4, column=1, **paddings)

        nameLstLabel = Label(fileSelFrame, text="Names list")
        nameLstEntry = Entry(fileSelFrame, width=60, **entry_font)
        nameLstSelBtn = Button(
            fileSelFrame,
            text="Select",
            command=lambda: self.browseFiles(nameLstEntry, [1]),
        )
        nameLstLabel.grid(sticky="W", row=6, column=0, **paddings)
        nameLstSelBtn.grid(row=6, column=2, **paddings)
        nameLstEntry.grid(row=6, column=1, **paddings)

        outputLabel = Label(fileSelFrame, text="Output location")
        outputEntry = Entry(fileSelFrame, width=60, **entry_font)
        outputSelBtn = Button(
            fileSelFrame,
            text="Select",
            command=lambda: self.browseFiles(outputEntry, openFile=False),
        )
        outputLabel.grid(sticky="W", row=8, column=0, **paddings)
        outputSelBtn.grid(row=8, column=2, **paddings)
        outputEntry.grid(row=8, column=1, **paddings)

        notificationFrame = Frame(self)
        notificationFrame.pack(**paddings)
        notificationLabel = Label(notificationFrame)
        notificationLabel.pack(**paddings)

        resultsFrame = Frame(self)
        resultsFrame.pack(**framePaddings)

        buttonFrame = Frame(self)
        buttonFrame.pack(side=BOTTOM, **framePaddings)
        generateBtn = Button(buttonFrame, text="Mark", command=self.mark)
        generateBtn.pack(side=LEFT)
        closeBtn = Button(buttonFrame, text="Close", command=self.destroy)
        closeBtn.pack(side=RIGHT)

        self.notificationLabel = notificationLabel
        self.correctAnsEntry = correctAnsEntry
        self.ansSheetEntry = ansSheetEntry
        self.nameLstEntry = nameLstEntry
        self.outputEntry = outputEntry
        self.resultsFrame = resultsFrame

    def browseFiles(self, entry, fileTypeIndices=[], openFile=True):
        if openFile:
            fileTypesMap = {
                0: ("Text files", "*.txt*"),
                1: ("CSV files", "*.csv*"),
                2: ("PDF files", "*.pdf*"),
                -1: ("all files", "*.*"),
            }
            filetypes = list(map(lambda index: fileTypesMap[index], fileTypeIndices))
            text = filedialog.askopenfilename(
                title="Select a File", filetypes=filetypes
            )
        else:
            text = filedialog.askdirectory(title="Select a Folder")

        entry.delete(0, END)
        entry.insert(0, text)

    def mark(self):
        try:
            (
                correct_answers_path,
                answer_sheet_pdf_path,
                names_list_path,
                output_path,
            ) = (
                self.correctAnsEntry.get(),
                self.ansSheetEntry.get(),
                self.nameLstEntry.get(),
                self.outputEntry.get(),
            )
            assert (
                correct_answers_path != ""
            ), "Correct answers csv file must not be empty"
            assert (
                answer_sheet_pdf_path != ""
            ), "Answer sheet pdf file must not be empty"

            results = markMCQ(
                correct_answers_path,
                answer_sheet_pdf_path,
                names_list_path,
                output_path,
            )
            self.show_results(results)
            self.notificationLabel.configure(
                text="Output saved!", background="lightgreen"
            )

        except AssertionError as e:
            self.show_error(e)
        except PermissionError as e:
            if str(e)[-12:] == "results.csv'":
                self.show_error(
                    "Error opening the results file. Make sure that the old results file is not open"
                )

    def show_error(self, message):
        self.notificationLabel.configure(text=message, background="pink")

    def show_results(self, results):
        # clear the frame
        for widget in self.resultsFrame.winfo_children():
            widget.destroy()

        containsNames = len(results[0]) == 4
        if containsNames:  # if the names are included
            Label(self.resultsFrame, text="#").grid(row=0, column=0)
            Label(self.resultsFrame, text="Name").grid(row=0, column=1)
            Label(self.resultsFrame, text="Score").grid(row=0, column=2)
        else:
            Label(self.resultsFrame, text="#").grid(row=0, column=0)
            Label(self.resultsFrame, text="Score").grid(row=0, column=1)

        for i, result in enumerate(results):
            Label(self.resultsFrame, text=i).grid(row=i + 1, column=0)
            if containsNames:
                Label(self.resultsFrame, text=results[i][0]).grid(row=i + 1, column=1)
                Label(self.resultsFrame, text=results[i][-1]).grid(row=i + 1, column=2)
            else:
                Label(self.resultsFrame, text=results[i][-1]).grid(row=i + 1, column=1)


if __name__ == "__main__":
    app = App()
    app.mainloop()
