//
// Created by https://github.com/CardinalPanda
//
//Licensed under the GNU General Public License Version 3 (GNU GPL v3),
//    available at: https://www.gnu.org/licenses/gpl-3.0.txt

// THIS IS A MULTITHREAD WIP BY TREMESCHIN
// Seems like everything works as expected
// and got a sec or two faster, about a plus 2% 
// improvement on top of the old optimizations I made

#ifndef DANDERE2X_DRIVER_H
#define DANDERE2X_DRIVER_H

#include "Plugins/Correction/Correction.h"
#include "Plugins/PFrame/PFrame.h"
#include "Plugins/Fade/Fade.h"

#include "Dandere2xUtils/Dandere2xUtils.h"
#include "Image/DebugImage/DebugImage.h"

//tremx
#include <thread>
#include <cmath> 


/**
 * Todo:
 * - Simplify this driver class
 * - Add ability to test individual parts
 */


/**
 * Description:
 *
 * This is like the control room for Dandere2x - if you wish to add more additions to Dandere2x on the c++ side,
 * this where it is going to do it here.  Block matching, quality control, and saving of vectors all happen here.
 */
using namespace dandere2x;
using namespace std;
const int correction_block_size = 2;

#include <chrono>
using namespace std::chrono;

// made the original for loop into a function to multithread it

void diff(int x, string image_prefix, string compressed_static_prefix, string compressed_moving_prefix,
          string p_data_prefix, string difference_prefix, string correction_prefix, string fade_prefix,
          int block_size, int step_size, string extension_type) {
    
    shared_ptr<Image> image_1 = make_shared<Image>(image_prefix + to_string(x) + extension_type);
    

    auto frame_time_start = high_resolution_clock::now();
    cout << "  Computing differences for frame: " << x << endl;

    // Create strings for the files we need to interact with for this computation iteration
    string image_2_file = image_prefix + to_string(x + 1) + extension_type;
    string image_2_compressed_static_file = compressed_static_prefix + to_string(x + 1) + ".jpg";
    string image_2_compressed_moving_file = compressed_moving_prefix + to_string(x + 1) + ".jpg";

    // Wait for those files...
    dandere2x::wait_for_file(image_2_file);
    dandere2x::wait_for_file(image_2_compressed_static_file);
    dandere2x::wait_for_file(image_2_compressed_moving_file);

    // load actual images themselves
    shared_ptr<Image> image_2 = make_shared<Image>(image_2_file);
    shared_ptr<Image> image_2_copy = make_shared<Image>(image_2_file); //load im_2 twice for 'corrections'
    shared_ptr<Image> image_2_compressed_static = make_shared<Image>(image_2_compressed_static_file);
    shared_ptr<Image> image_2_compressed_moving = make_shared<Image>(image_2_compressed_moving_file);

    // Create strings for the files we need to save for this computation iteration
    string p_data_file = p_data_prefix + to_string(x) + ".txt";
    string difference_file = difference_prefix + to_string(x) + ".txt";
    string correction_file = correction_prefix + to_string(x) + ".txt";
    string fade_file = fade_prefix + to_string(x) + ".txt";
    
    /**
        *  ## Compute Plugins ##
        */

    // This is the area where we compute plugins. Note that the way D2x_cpp works, image_2 ends up becoming
    // Modified during each plugin run. Recall that our goal is to produce image_2 using as many parts
    // from image_1, so it makes sense to overwrite image_2 with parts of image_1 as we go along.

    // First run the 'fade' plugin, which checks if two frames are simply fade to black / fade to white
    Fade fade = Fade(image_1, image_2, image_2_compressed_static, block_size, fade_file);
    fade.run();

    // Find similar blocks between image_1 and image_2 and match them, and document which matched (p_data_file).
    // Document which blocks we could not find a match for, and add them to a list of missing blocks (difference_file)
    PFrame pframe = PFrame(image_1, image_2, image_2_compressed_static, image_2_compressed_moving, block_size, p_data_file, difference_file, step_size);
    pframe.run();

    // When finding similar blocks, there may be small blemishes left in as a result. Try our best
    // To find those errors, and replace them with nearby pixels. Use the original image as a reference
    // On how to preform these corrections.
    Correction correction = Correction(image_2, image_2_copy, image_2_compressed_static, correction_block_size, correction_file, 2);
    correction.run();

    // Save the results for Dandere2x_python to use
    pframe.save();
    fade.save();
    correction.save();

    // For Debugging. Create a folder called 'debug_frames' in workspace when testing this -
    // Enabling this will allow you to see what Dandere2x_Cpp is seeing when it finishes processing a frame.
    // DebugImage before = DebugImage::create_debug_from_image(*image_2);
    // before.save(workspace + "debug_frames" + separator() + "before_" + to_string(x) + ".png");


    // For the next iteration, we simply let frame 'x' become frame 'x+1'.
    // For example, when computing frame 100 -> 101, image_1=100 and image_2=101.
    // Assign image_1=101, so when computing 101 -> 102, 101 is already loaded.
    //image_1 = image_2;

    ///auto stop = high_resolution_clock::now();
    ///auto duration = duration_cast<microseconds>(stop - frame_time_start);
    ///cout << "Calculation time for frame :  " <<  duration.count() << endl;
}

void driver_difference(string workspace, int resume_count, int frame_count,
                       int block_size, int step_size, string extension_type)  {


    // Create pre-fixes for all the files needed to be accessed during dandere2x's runtime.
    // We do this primarly for readibility / maintability, as the files Dandere2x needs to
    // Interact with is very consistent in naming.

    string image_prefix = workspace + separator() + "inputs" + separator() + "frame";
    string p_data_prefix = workspace + separator() + "pframe_data" + separator() + "pframe_";
    string difference_prefix = workspace + separator() + "inversion_data" + separator() + "inversion_";
    string correction_prefix = workspace + separator() + "correction_data" + separator() + "correction_";
    string fade_prefix = workspace + separator() + "fade_data" + separator() + "fade_";
    string compressed_static_prefix = workspace + separator() + "compressed_static" + separator() + "compressed_";
    string compressed_moving_prefix = workspace + separator() + "compressed_moving" + separator() + "compressed_";
   // DANDERE2x_CPP DRIVER STARTS HERE //

   // Before we start anything, we need to load the gensises image, image_1. This is because the first
   // Image is treated sort of differently in Dandere2x - it's the only image we can gurantee it is a 'i' frame,
   // And the entire image needs to be loaded.
    shared_ptr<Image> image_1 = make_shared<Image>(image_prefix + to_string(1) + extension_type);

    // Dandere2x_cpp Handles the resume case by leaving everything empty, which serves as a signal to
    // Dandere2x_python simply draw a new frame at the resume frame.
    // Each plugin needs to have it's own 'resume' handling case.
    if (resume_count != 1) {

        shared_ptr<Image> im2 = make_shared<Image>(image_prefix + to_string(resume_count + 1) + extension_type);

        string p_data_file = p_data_prefix + to_string(resume_count) + ".txt";
        string difference_file = difference_prefix + to_string(resume_count) + ".txt";
        string correction_file = correction_prefix + to_string(resume_count) + ".txt";
        string fade_file = fade_prefix + to_string(resume_count) + ".txt";

        write_empty(p_data_file);
        write_empty(difference_file);
        write_empty(correction_file);
        write_empty(fade_file);

        image_1 = im2;

        resume_count++;
    }

    auto total_start = high_resolution_clock::now();

    // Note that if Dandere2x is a new session, resume_count = 0.
    // Simply put, this for loop right here is pretty much the control room for 99% of the stuff
    // Happening within Dandere2x. The saving of files, the calculation of vectors, the loading of
    // Images all happens here.

    // The goal of this is, given frame_x, try and draw frame_x+1 using parts of x.
    // The 'plugins' section of this loop is a series of tools to help us achieve that.
    



    //std::thread t[concurentThreadsSupported];

    //int numthread;


    //give dandere2x something to work before creating tons of threads
    
    //float limitToMultithreadPercentage = 5;

    //int firstFramesPercentage = (int)round((limitToMultithreadPercentage/100) * frame_count);

    /*
    if (frame_count <= 60) { // too low to multithread
        
        std::cout << "Too low to multithread." << endl;

        for (int k = resume_count; k < frame_count; k++) {
            diff(k, image_prefix, compressed_static_prefix, compressed_moving_prefix, p_data_prefix,
                            difference_prefix, correction_prefix, fade_prefix, block_size, step_size, extension_type);
        }

    } else {
        
        std::cout << "Single threading " << firstFramesPercentage << " first diffs, frame_count = " << frame_count << endl;

        for (int k = resume_count; k < firstFramesPercentage; k++) {
            diff(k, image_prefix, compressed_static_prefix, compressed_moving_prefix, p_data_prefix,
                            difference_prefix, correction_prefix, fade_prefix, block_size, step_size, extension_type);
        }
        */


    // tremx tryharding on cpp with only python knowledge part 2 - multithread the beast
    // after all those failed trys, this is the one that worked


    // get system thread count on cpu?
    unsigned concurentThreadsSupported = std::thread::hardware_concurrency();

    cout << "Maximun ideal concurrent threads in this system: " << concurentThreadsSupported << endl;

    // create a threads list to put them here aind wait them to finish in batches
    std::vector<std::thread> threads;

    std::cout << "Staring the multithread proccess" << endl;

    // could rename this var but left here for readability
    int batchSamples = concurentThreadsSupported;

    batchSamples -= 1; // to compensate the <= in the for loop

    // fail safe if running on a.. 0 core cpu? xD
    if (batchSamples < 0) {
        batchSamples = 0;
    }
    // the threads uses memory, ~60 MB per thread,
    // is it a good move to limit this number?
    // btw no one with a Ryzen 9 3950x; i9 9900k; Epyc or Xenon
    // gonna have only 4 GBs of Ram.. ? Not limiting this by now
    // 2 GB of ram on a 32 threads system, not good but not worse.
    
    int imgnum;

    // make K in this loop add batchSamples time every loop

    for (int k = resume_count; k < frame_count; k = k + batchSamples + 1) {

        // batches of batchSamples times each, that's why we defined imgnum beforehand
        for (int curBatch = 0; curBatch <= batchSamples; curBatch++ ) {

            imgnum = k+curBatch;
            
            // we don't want to thread the last image because there's not a frame_count + 1 image
            if (imgnum < frame_count) {
                
                // thread the whole original thing into that first function
                threads.push_back(std::thread (diff, imgnum, image_prefix, compressed_static_prefix, compressed_moving_prefix, p_data_prefix,
                                    difference_prefix, correction_prefix, fade_prefix, block_size, step_size, extension_type));
            }
        }
        // wait to finish the batchSamples threads
        for(auto& thread : threads){
            thread.join();
        }

        // clear the thread list - we can't join finished threads
        threads.clear();
    }

    auto total_end = high_resolution_clock::now();
    auto total_duration = duration_cast<microseconds>(total_end - total_start);

    cout << "total time:  " << (float)total_duration.count()/1000000 << "s" << endl;
}

#endif //DANDERE2X_DRIVER_H
