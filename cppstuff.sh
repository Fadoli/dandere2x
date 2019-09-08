# Linux only file to compile and move the binary from cpp

cd ../dandere2x_cpp
cmake CMakeLists.txt
make -j$(expr $(nproc) \+ 1)
cd ..
mv dandere2x_cpp/dandere2x_cpp src/externals/dandere2x_cpp
