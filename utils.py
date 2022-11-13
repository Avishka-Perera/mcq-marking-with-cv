from cv2 import cvtColor, COLOR_BGR2GRAY, Canny, HoughLines, getPerspectiveTransform, warpPerspective
from fitz import open as fitz_open, Pixmap as fitz_Pixmap, csRGB as fitz_csRGB
from PIL import Image
from pandas import read_csv
from numpy import array, pi, sin, cos, inf, float32

def getImagesFromPDF(file_name):
    img_lst = []
    doc = fitz_open(file_name)
    for i in range(len(doc)):
        for img in doc.get_page_images(i):
            xref = img[0]
            pix = fitz_Pixmap(doc, xref)
            if pix.n >= 5:       # this is CMYK (not GRAY or RGB) so convert to RGB first
                pix = fitz_Pixmap(fitz_csRGB, pix)

            mode = "RGBA" if pix.alpha else "RGB"
            img = array(Image.frombytes(mode, [pix.width, pix.height], pix.samples))
            if img.shape[0] > 270: # this is to skip the camscanner logo which is of shape (260, 260, 3)
                img_lst.append(("p%s-%s.png" % (i, xref), img))

            pix = None
    doc.close()

    return img_lst

# computational functions
def getIntersectionPoint(line1, line2):
    rho1, theta1 = line1[0], line1[1]
    rho2, theta2 = line2[0], line2[1]
    x = int((rho1*sin(theta2)-rho2*sin(theta1))/(sin(theta2-theta1)))
    y = int((rho2*cos(theta1)-rho1*cos(theta2))/(sin(theta2-theta1)))
    return x, y

# constants
mcq_grid_orig_dim = (1109.6, 517.6)
table_size = tuple(map(int, mcq_grid_orig_dim))
mcq_grid_cell_marg = 5
border_width = 2

# Trims the answers table
def extractMCQTable(mcq_sheet):
    # fine tune constants
    canny_min_threshold = 20
    canny_max_threshold = 80
    canny_apertureSize = 3
    hough_votes_vert_density = 200  # makes the vote count dependant to the image dimensions
    hough_votes_hori_density = 500  # makes the vote count dependant to the image dimensions
    hough_theta_max_variation_deg = 2

    hough_votes_vert = int(hough_votes_vert_density/mcq_sheet.shape[0]*900)
    hough_votes_hori = int(hough_votes_hori_density/mcq_sheet.shape[1]*1200)
    hough_theta_max_variation = hough_theta_max_variation_deg/180*pi

    gray = cvtColor(mcq_sheet, COLOR_BGR2GRAY)

    # detect houghlines
    edges = Canny(gray, canny_min_threshold, canny_max_threshold, canny_apertureSize)
    horizontal_lines = HoughLines(edges, 1, pi/180, hough_votes_hori, min_theta=pi/2-hough_theta_max_variation, max_theta=pi/2+hough_theta_max_variation)
    vertical_lines = HoughLines(edges, 1, pi/180, hough_votes_vert, min_theta=0, max_theta=+hough_theta_max_variation)
    
    left_most_line, right_most_line, top_most_line, bottom_most_line = None, None, None, None
    max_val, min_val = 0, inf
    for line in horizontal_lines:
        if line[0][0]<min_val:
            left_most_line = line[0]
            min_val = line[0][0]
        if line[0][0]>max_val:
            right_most_line = line[0]
            max_val = line[0][0]
    max_val, min_val = 0, inf
    for line in vertical_lines:
        if line[0][0]<min_val:
            top_most_line = line[0]
            min_val = line[0][0]
        if line[0][0]>max_val:
            bottom_most_line = line[0]
            max_val = line[0][0]

    detected_img = mcq_sheet.copy()

    # get the corner points
    top_left = getIntersectionPoint(top_most_line, left_most_line)
    top_right = getIntersectionPoint(top_most_line, right_most_line)
    bottom_left = getIntersectionPoint(bottom_most_line, left_most_line)
    bottom_right = getIntersectionPoint(bottom_most_line, right_most_line)

    # apply homography
    contract_val = border_width
    H = getPerspectiveTransform(float32((top_left, top_right, bottom_right, bottom_left)), float32((
        (-contract_val, -contract_val),
        (-contract_val, +contract_val+mcq_grid_orig_dim[1]),
        (+contract_val+mcq_grid_orig_dim[0], +contract_val+mcq_grid_orig_dim[1]),
        (+contract_val+mcq_grid_orig_dim[0], -contract_val)
    )))
    mcq_table = warpPerspective(mcq_sheet, H, table_size)

    return mcq_table

# Divides the regions and read the data

def getQuestionRegion(mcq_table, table_size, question_number):
    assert type(question_number) == int
    assert question_number <= 50
    question_region_padding = 5
    row = (question_number-1)%10
    col = int((question_number-1)/10)
    region_w = table_size[0]/5
    region_h = table_size[1]/10
    question_region = mcq_table[int(row*region_h+question_region_padding):int((row+1)*region_h-question_region_padding), int(col*region_w+question_region_padding):int((col+1)*region_w-question_region_padding)]

    return question_region

def getSelectedAnswer(mcq_table, table_size, question_number):
    question_number_width, answers_width = 30, 178
    answers_region_padding = 4
    question_region = getQuestionRegion(mcq_table, table_size, question_number)
    question_width = question_region.shape[1]
    answers_region = question_region[:,int(answers_region_padding+question_width*question_number_width/(question_number_width + answers_width)):-answers_region_padding]
    answer_width = answers_region.shape[1]/5

    # select the answer which has been colored (darkest)
    min_intensity, selected_answer = inf, 0
    for i in range(5):
        intensity = answers_region[:,int(i*answer_width):int((i+1)*answer_width)].sum()
        if intensity < min_intensity:
            min_intensity = intensity
            selected_answer = i+1
    
    return selected_answer

def exportData(data, filename):
    out_str = "name,selected_answers, correct, score\n"
    out_str += "\n".join(list(map(lambda x: ",".join(list(map(str, x))), data)))
    with open(filename, "w") as f:
        f.write(out_str)

def markMCQ(correct_answers_path, answer_sheet_pdf_path, names_list_path, output_path):
    correct_answers = read_csv(correct_answers_path)
    img_lst = getImagesFromPDF(answer_sheet_pdf_path)
    names = None
    if names_list_path != "":
        names = read_csv(names_list_path, header=None)
        assert len(names) == len(img_lst), "Answer script count in the pdf is not similar to the number of names"
        names = names.iloc()

    results = []

    for i, img in enumerate(img_lst):
        mcq_sheet = img[1]
        mcq_table = extractMCQTable(mcq_sheet)
        selected_answers = ""
        correct = ""
        score = 0
        for row in correct_answers.iloc():
            q_num = row["question"]
            correct_answer = row["answer"]
            selected_answer = getSelectedAnswer(mcq_table, table_size, int(q_num))
            selected_answers += str(selected_answer)
            if selected_answer == correct_answer:
                correct += "1"
                score += 1
            else:
                correct += "0"
                
        if names is not None:
            results.append((names[i][0], selected_answers, correct, score))
        else:
            results.append((selected_answers, correct, score))

    exportData(results, f"{output_path}/results.csv")
    
    return results
        